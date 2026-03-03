#!/usr/bin/env python3
"""
Weather Satellite Image Dumper
Downloads images from FTP server and organizes them by date
"""

import os
from ftplib import FTP, error_perm
import logging
from datetime import datetime, timedelta
import time
from pathlib import Path
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SatelliteImageDownloader:
    def __init__(self, host='ntsomz.gptl.ru', port=2121, 
                 username='electro', password='electro'):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_path = '/ELECTRO_L_3/2026/'
        self.local_base = Path('images')
        self.local_base.mkdir(exist_ok=True)
        
        # Month mappings
        self.months = {
            'January': '01', 'February': '02', 'March': '03',
            'April': '04', 'May': '05', 'June': '06',
            'July': '07', 'August': '08', 'September': '09',
            'October': '10', 'November': '11', 'December': '12'
        }

    def connect_ftp(self):
        """Establish FTP connection"""
        try:
            ftp = FTP()
            ftp.connect(self.host, self.port, timeout=30)
            ftp.login(self.username, self.password)
            ftp.set_pasv(True)
            logger.info(f"Connected to {self.host}:{self.port}")
            return ftp
        except Exception as e:
            logger.error(f"FTP connection failed: {e}")
            return None

    def get_time_folders(self, ftp, base_dir):
        """Get all time folders (like 0115, 0145, etc.) in a directory"""
        try:
            ftp.cwd(base_dir)
            items = ftp.nlst()
            # Filter for time folders (4 digits)
            time_folders = [item for item in items if len(item) == 4 and item.isdigit()]
            return time_folders
        except Exception as e:
            logger.debug(f"Could not list time folders in {base_dir}: {e}")
            return []

    def download_file(self, ftp, remote_path, local_path):
        """Download a single file"""
        try:
            # Create local directory if it doesn't exist
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file already exists
            if local_path.exists():
                logger.debug(f"File already exists: {local_path}")
                return False
            
            # Download file
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {remote_path}', f.write)
            
            logger.info(f"✅ Downloaded: {remote_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading {remote_path}: {e}")
            return False

    def scan_and_download(self, days_back=2):
        """Scan FTP server and download new images"""
        ftp = self.connect_ftp()
        if not ftp:
            return 0
        
        downloaded_count = 0
        scanned_count = 0
        
        try:
            # Calculate date range to check
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            current_date = start_date
            while current_date <= end_date:
                month_num = current_date.strftime('%m')
                day = current_date.strftime('%d')
                
                # Get month name
                month_name = None
                for name, num in self.months.items():
                    if num == month_num:
                        month_name = name
                        break
                
                if not month_name:
                    current_date += timedelta(days=1)
                    continue
                
                logger.info(f"Checking: 2026/{month_name}/{day}")
                
                # Construct day directory path
                day_dir = f"{self.base_path}{month_name}/{day}/"
                
                try:
                    # Change to day directory
                    ftp.cwd(day_dir)
                    
                    # Get all time folders (0115, 0145, etc.)
                    time_folders = self.get_time_folders(ftp, day_dir)
                    
                    if not time_folders:
                        logger.debug(f"No time folders found in {day_dir}")
                        current_date += timedelta(days=1)
                        continue
                    
                    # Check each time folder for images
                    for time_folder in time_folders:
                        time_dir = f"{day_dir}{time_folder}/"
                        
                        try:
                            ftp.cwd(time_dir)
                            files = ftp.nlst()
                            
                            # Look for RGB VIS IR images
                            for filename in files:
                                if filename.endswith('.jpg') and 'original_RGB_VIS_IR' in filename:
                                    scanned_count += 1
                                    remote_path = f"{time_dir}{filename}"
                                    
                                    # Create local path: images/2026/MM/DD/filename
                                    local_path = self.local_base / '2026' / month_num / day / filename
                                    
                                    if self.download_file(ftp, remote_path, local_path):
                                        downloaded_count += 1
                                        
                        except Exception as e:
                            logger.debug(f"Could not access {time_dir}: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Could not access {day_dir}: {e}")
                
                current_date += timedelta(days=1)
            
            logger.info(f"📊 Scan complete. Found: {scanned_count} matching files, Downloaded: {downloaded_count} new files")
            return downloaded_count
            
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            return downloaded_count
        finally:
            try:
                ftp.quit()
            except:
                pass

def main():
    parser = argparse.ArgumentParser(description='Download weather satellite images')
    parser.add_argument('--days', type=int, default=2, help='Days back to scan')
    parser.add_argument('--continuous', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, default=30, help='Minutes between scans')
    args = parser.parse_args()
    
    downloader = SatelliteImageDownloader()
    
    if args.continuous:
        logger.info(f"Starting continuous monitoring (interval: {args.interval} minutes)")
        while True:
            try:
                count = downloader.scan_and_download(days_back=args.days)
                if count > 0:
                    logger.info(f"Downloaded {count} new images")
                
                logger.info(f"Waiting {args.interval} minutes until next scan...")
                time.sleep(args.interval * 60)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(300)
    else:
        downloader.scan_and_download(days_back=args.days)

if __name__ == "__main__":
    main()
