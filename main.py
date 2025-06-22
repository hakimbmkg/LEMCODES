import argparse
from preprocess import Preprocess

def main():
    parser = argparse.ArgumentParser(description="Downloader FDSN dengan multiproses dan resume")
    parser.add_argument("--client", required=False, help="Nama client FDSN, misalnya IRIS, ORFEUS, BMKG, dll.")
    parser.add_argument("--network", required=False, help="Kode network, bisa multiple dipisah koma")
    parser.add_argument("--station", required=False, help="Kode stasiun, bisa multiple dipisah koma")
    parser.add_argument("--channel", required=False, help="Channel yang ingin diambil, contoh: EHZ,EHN,EHZ")
    parser.add_argument("--start", required=False, help="Tanggal mulai (format: YYYY-MM-DD)")
    parser.add_argument("--end", required=False, help="Tanggal akhir (format: YYYY-MM-DD)")
    parser.add_argument("--output_dir", default="Program", help="Folder output utama")
    parser.add_argument("--threads", type=int, default=4, help="Jumlah thread untuk paralel download")
    parser.add_argument("--only_station_list", action="store_true", help="Hanya ambil daftar stasiun")
    parser.add_argument("--only_download", action="store_true", help="Hanya download waveform dari station_list.csv")
    parser.add_argument("--resume_failed", action="store_true", help="Melanjutkan download yang gagal sebelumnya")
    parser.add_argument("--force_new", action="store_true", help="Paksa buat folder baru meskipun sudah ada")

    args = parser.parse_args()

    process = Preprocess(
        client_name=args.client,
        network=args.network,
        station=args.station,
        channel=args.channel,
        start=args.start,
        end=args.end,
        output_dir=args.output_dir,
        threads=args.threads,
        force_new=args.force_new
    )

    process.setup_folder()

    if args.only_station_list:
        process.download_station_list()
        return

    if args.only_download:
        process.download_station_list()
        process.download_waveforms()
        return

    if args.resume_failed:
        process.resume_failed_downloads()
        return

    process.download_station_list()
    process.download_waveforms()

if __name__ == "__main__":
    main()
