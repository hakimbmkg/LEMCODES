import os
import csv
import time
from datetime import datetime, timedelta
from obspy.clients.fdsn import Client
from obspy import UTCDateTime, read
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from datetime import datetime as dt

class Preprocess:
    def __init__(self, client_name, network, station, channel, start, end, output_dir="Program", threads=4, force_new=False):
        self.client = Client(client_name,user="admin",password="admin")
        self.networks = network.split(",")
        self.stations = station.split(",") if station else []
        self.channels = channel.split(",") if channel else []
        self.start_date = datetime.strptime(start, "%Y-%m-%d") if start else None
        self.end_date = datetime.strptime(end, "%Y-%m-%d") if end else None
        self.output_dir = output_dir
        self.waveform_dir = os.path.join(output_dir, "Waveform")
        self.station_csv = os.path.join(output_dir, "station_list.csv")
        self.log_file = os.path.join(output_dir, "logfile.log")
        self.resume_file = os.path.join(output_dir, "resume_list.txt")
        self.threads = threads
        self.force_new = force_new
        self.station_list = []

    def setup_folder(self):
        if os.path.exists(self.output_dir) and not self.force_new:
            print(f"[INFO] Menggunakan folder lama: {self.output_dir}")
        else:
            os.makedirs(self.output_dir, exist_ok=True)
            print(f"[INFO] Folder '{self.output_dir}' dibuat.")
        os.makedirs(self.waveform_dir, exist_ok=True)
        print(f"[INFO] Subfolder 'Waveform' disiapkan.")

    def download_station_list(self):
        if os.path.exists(self.station_csv):
            print(f"[INFO] File station_list.csv ditemukan. Menggunakan konfigurasi yang ada.")
            with open(self.station_csv, 'r') as f:
                reader = csv.DictReader(f)
                self.station_list = [row for row in reader]
            return

        print("[INFO] Mengambil daftar stasiun dari server...")
        from obspy.core.inventory import Inventory
        for net in self.networks:
            try:
                inv: Inventory = self.client.get_stations(
                    network=net,
                    level="channel",
                    station=",".join(self.stations) if self.stations else None,
                    channel=",".join(self.channels) if self.channels else None,
                    starttime=UTCDateTime(self.start_date),
                    endtime=UTCDateTime(self.end_date)
                )
                for n in inv:
                    for sta in n:
                        for chan in sta:
                            self.station_list.append({
                                "network": n.code,
                                "station": sta.code,
                                "location": chan.location_code or "",
                                "channel": chan.code
                            })
            except Exception as e:
                print(f"[WARNING] Gagal ambil stasiun dari network {net}: {e}")

        with open(self.station_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["network", "station", "location", "channel"])
            writer.writeheader()
            for s in self.station_list:
                writer.writerow(s)

        print(f"[INFO] Total stasiun-channel: {len(self.station_list)} disimpan ke {self.station_csv}")

    def is_valid_mseed(self, file_path, min_duration=1):
        try:
            if not os.path.exists(file_path) or os.path.getsize(file_path) < 1024:
                return False
            st = read(file_path)
            duration = st[-1].stats.endtime - st[0].stats.starttime
            return duration >= min_duration
        except Exception:
            return False

    def log_mseed_csv(self, fpath, station, start_time, duration):
        csv_path = os.path.join(self.output_dir, "fname.csv")
        is_new = not os.path.exists(csv_path)
        status = "lengkap" if duration >= 86400 * 0.9 else "parsial"

        with open(csv_path, "a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=[
                "filename", "network", "station", "location", "channel", "start_time", "duration", "status"
            ])
            if is_new:
                writer.writeheader()
            writer.writerow({
                "filename": os.path.basename(fpath),
                "network": station["network"],
                "station": station["station"],
                "location": station["location"],
                "channel": station["channel"],
                "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "duration": round(duration),
                "status": status
            })

    def _download_one(self, station, date):
        from obspy import Stream
        net = station["network"]
        sta = station["station"]
        loc = station["location"]
        chan = station["channel"]

        fname = f"{net}.{sta}.{loc}.{chan}.{date.strftime('%Y-%m-%dT%H:%M:%S')}.mseed"
        fpath = os.path.join(self.waveform_dir, fname)

        logtime = dt.now().strftime("%Y-%m-%d %H:%M:%S")

        if os.path.exists(fpath) and self.is_valid_mseed(fpath):
            with open(self.log_file, 'a') as f:
                f.write(f"[{logtime}] SKIP   : {fpath} sudah valid, dilewati.\n")
            return

        try:
            st: Stream = self.client.get_waveforms(
                network=net,
                station=sta,
                location=loc,
                channel=chan,
                starttime=UTCDateTime(date),
                endtime=UTCDateTime(date + timedelta(days=1))
            )
            st.write(fpath, format="MSEED")

            duration = st[-1].stats.endtime - st[0].stats.starttime
            self.log_mseed_csv(fpath, station, st[0].stats.starttime.datetime, duration)

            if duration < 86400 * 0.9:
                logmsg = f"[{logtime}] SUKSES : {fpath} (parsial {duration:.1f} detik)\n"
            else:
                logmsg = f"[{logtime}] SUKSES : {fpath}\n"

            with open(self.log_file, 'a') as f:
                f.write(logmsg)

        except Exception as e:
            with open(self.log_file, 'a') as f:
                f.write(f"[{logtime}] GAGAL  : {net}.{sta}.{chan} {date} - ERROR: {str(e)}\n")
            with open(self.resume_file, 'a') as f:
                f.write(f"{net},{sta},{loc},{chan},{date.strftime('%Y-%m-%d')}\n")

    def download_waveforms(self):
        if not self.station_list:
            raise ValueError("Station list kosong. Jalankan download_station_list() lebih dulu.")
        print("[INFO] Mulai download waveform...")
        start_time = time.time()

        tasks = []
        for s in self.station_list:
            d = self.start_date
            while d < self.end_date:
                fname = f"{s['network']}.{s['station']}.{s['location']}.{s['channel']}.{d.strftime('%Y-%m-%dT%H:%M:%S')}.mseed"
                fpath = os.path.join(self.waveform_dir, fname)
                if not os.path.exists(fpath) or not self.is_valid_mseed(fpath):
                    tasks.append((s, d))
                d += timedelta(days=1)

        print(f"[INFO] Total file untuk didownload: {len(tasks)}")
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(self._download_one, s, d) for s, d in tasks]
            for _ in tqdm(futures):
                _.result()

        elapsed = time.time() - start_time
        summary = f"[{dt.now().strftime('%Y-%m-%d %H:%M:%S')}] SELESAI: Download {len(tasks)} file dalam {elapsed:.2f} detik.\n"
        print(summary)
        with open(self.log_file, 'a') as f:
            f.write(summary)

    def resume_failed_downloads(self):
        if not os.path.exists(self.resume_file):
            print("[INFO] Tidak ada resume_list.txt ditemukan.")
            return

        print("[INFO] Melanjutkan proses dari resume_list.txt...")
        start_time = time.time()

        tasks = []
        with open(self.resume_file, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) != 5:
                    continue
                net, sta, loc, chan, date_str = parts
                date = datetime.strptime(date_str, "%Y-%m-%d")
                station = {
                    "network": net,
                    "station": sta,
                    "location": loc,
                    "channel": chan
                }
                fname = f"{net}.{sta}.{loc}.{chan}.{date.strftime('%Y-%m-%dT%H:%M:%S')}.mseed"
                fpath = os.path.join(self.waveform_dir, fname)
                if not os.path.exists(fpath) or not self.is_valid_mseed(fpath):
                    tasks.append((station, date))

        print(f"[INFO] Total file gagal yang akan dicoba ulang: {len(tasks)}")
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(self._download_one, s, d) for s, d in tasks]
            for _ in tqdm(futures):
                _.result()

        elapsed = time.time() - start_time
        summary = f"[{dt.now().strftime('%Y-%m-%d %H:%M:%S')}] SELESAI: Resume {len(tasks)} file dalam {elapsed:.2f} detik.\n"
        print(summary)
        with open(self.log_file, 'a') as f:
            f.write(summary)
