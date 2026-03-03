import os
import ftplib
from datetime import datetime

FTP_HOST = "ntsomz.gptl.ru"
FTP_PORT = 2121
FTP_USER = "electro"
FTP_PASS = "electro"

IMAGE_ROOT_PATH = "/ELECTRO_L_3/2026/"

LOCAL_SAVE_ROOT = "images"

def connect_ftp():
    ftp = ftplib.FTP()
    ftp.connect(FTP_HOST, FTP_PORT)
    ftp.login(FTP_USER, FTP_PASS)
    return ftp

def get_latest_month_day(ftp):
    ftp.cwd(IMAGE_ROOT_PATH)
    months = sorted(ftp.nlst())  # Expecting months as '01', '02', ..., not names
    if not months:
        return None, None
    latest_month = months[-1]
    ftp.cwd(latest_month)
    days = sorted(ftp.nlst())
    if not days:
        return latest_month, None
    latest_day = days[-1]
    ftp.cwd("..")
    return latest_month, latest_day

def list_new_images(ftp, year, month, day):
    path = f"{IMAGE_ROOT_PATH}{month}/{day}/"
    try:
        ftp.cwd(path)
        files = [f for f in ftp.nlst() if f.endswith(".jpg")]
        return files
    except Exception:
        return []

def download_image(ftp, remote_path, local_path):
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "wb") as f:
        ftp.retrbinary(f"RETR {remote_path}", f.write)

def already_downloaded(local_path):
    return os.path.exists(local_path)

def main():
    os.makedirs(LOCAL_SAVE_ROOT, exist_ok=True)
    ftp = connect_ftp()
    year = "2026"
    latest_month, latest_day = get_latest_month_day(ftp)
    if not latest_month or not latest_day:
        print("No month/day found on FTP.")
        return
    print(f"Processing: Year: {year}, Month: {latest_month}, Day: {latest_day}")
    images = list_new_images(ftp, year, latest_month, latest_day)
    print(f"Found {len(images)} image(s) in {latest_month}/{latest_day}.")
    for img in images:
        remote_img_path = f"{IMAGE_ROOT_PATH}{latest_month}/{latest_day}/{img}"
        local_img_path = os.path.join(LOCAL_SAVE_ROOT, year, latest_month, latest_day, img)
        if already_downloaded(local_img_path):
            print(f"Already downloaded: {img}")
            continue
        try:
            print(f"Downloading {img} ...")
            download_image(ftp, remote_img_path, local_img_path)
        except Exception as e:
            print(f"Failed to download {img}: {e}")
    ftp.quit()

if __name__ == "__main__":
    main()
