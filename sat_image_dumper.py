#!/usr/bin/env python3
"""
Weather Satellite Image Dumper
Downloads images from FTP server and organizes them by date
"""

import os
import sys
from ftplib import FTP, error_perm
import logging
from datetime import datetime, timedelta
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('downloader.log'),
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
        
        # Time slots to check
        self.time_slots = ['0000', '0030', '0100', '0130', '0200', 
                          '0230', '0300', '0330', '0400', '0430',
                          '0500', '0530', '0600', '0630', '0700',
                          '0730', '0800', '0830', '0900', '0930',
                          '1000', '1030', '1100', '1130', '1200',
                          '1230', '1300', '1330', '1400', '1430',
                          '1500', '1530', '1600', '1630', '1700',
                          '1730', '1800', '1830', '1900', '1930',
                          '2000', '2030', '2100', '2130', '2200',
                          '2230', '2300', '2330']

    def connect_ftp(self):
        """Establish FTP connection"""
        try:
            ftp = FTP()
            ftp.connect(self.host, self.port)
            ftp.login(self.username, self.password)
            logger.info(f"Connected to {self.host}:{self.port}")
            return ftp
        except Exception as e:
            logger.error(f"FTP connection failed: {e}")
            return None

    def get_remote_files(self, ftp, path):
        """Get list of files in remote directory"""
        try:
            files = []
            ftp.retrlines(f'LIST {path}', files.append)
            return files
        except error_perm as e:
            logger.debug(f"Directory {path} not accessible: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return []

    def parse_file_info(self, file_line):
        """Parse FTP LIST output to get filename"""
        # Handle different FTP LIST formats
        parts = file_line.split()
        if len(parts) > 8:
            # Typical format: -rw-r--r-- 1 user group size month day time filename
            return ' '.join(parts[8:])
        return None

    def download_file(self, ftp, remote_path, local_path):
        """Download a single file"""
        try:
            # Create local directory if it doesn't exist
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file already exists
            if local_path.exists():
                logger.info(f"File already exists: {local_path}")
                return False
            
            # Download file
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {remote_path}', f.write)
            
            logger.info(f"Downloaded: {remote_path} -> {local_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading {remote_path}: {e}")
            return False

    def scan_and_download(self, days_back=1):
        """Scan FTP server and download new images"""
        ftp = self.connect_ftp()
        if not ftp:
            return
        
        downloaded_count = 0
        
        try:
            # Calculate date range to check
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            current_date = start_date
            while current_date <= end_date:
                year = current_date.strftime('%Y')
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
                
                logger.info(f"Checking date: {year}/{month_name}/{day}")
                
                # Construct remote path
                remote_dir = f"{self.base_path}{month_name}/{day}/"
                
                # Get files in directory
                file_listing = self.get_remote_files(ftp, remote_dir)
                
                if not file_listing:
                    logger.debug(f"No files found in {remote_dir}")
                    current_date += timedelta(days=1)
                    continue
                
                # Process each file
                for file_line in file_listing:
                    filename = self.parse_file_info(file_line)
                    if not filename or not filename.endswith('.jpg'):
                        continue
                    
                    # Check if it matches the pattern (contains time and is RGB image)
                    if any(slot in filename for slot in self.time_slots):
                        if '_original_RGB_VIS_IR.jpg' in filename:
                            remote_path = f"{remote_dir}{filename}"
                            local_path = self.local_base / year / month_num / day / filename
                            
                            if self.download_file(ftp, remote_path, local_path):
                                downloaded_count += 1
                
                current_date += timedelta(days=1)
            
            logger.info(f"Download complete. Total new files: {downloaded_count}")
            
        except Exception as e:
            logger.error(f"Error during scan: {e}")
        finally:
            ftp.quit()

    def continuous_monitor(self, interval_minutes=30):
        """Continuously monitor for new images"""
        logger.info(f"Starting continuous monitoring (checking every {interval_minutes} minutes)")
        
        while True:
            try:
                self.scan_and_download(days_back=2)  # Check last 2 days
                logger.info(f"Waiting {interval_minutes} minutes until next scan...")
                time.sleep(interval_minutes * 60)
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(300)  # Wait 5 minutes on error

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Download weather satellite images')
    parser.add_argument('--days', type=int, default=1,
                       help='Number of days back to scan (default: 1)')
    parser.add_argument('--continuous', action='store_true',
                       help='Run in continuous monitoring mode')
    parser.add_argument('--interval', type=int, default=30,
                       help='Minutes between scans in continuous mode (default: 30)')
    
    args = parser.parse_args()
    
    downloader = SatelliteImageDownloader()
    
    if args.continuous:
        downloader.continuous_monitor(interval_minutes=args.interval)
    else:
        downloader.scan_and_download(days_back=args.days)

if __name__ == "__main__":
    main()
