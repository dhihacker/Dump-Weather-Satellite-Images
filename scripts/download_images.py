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
        
        # Month mappings (name -> number)
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
            logger.info(f"✅ Connected to {self.host}:{self.port}")
            return ftp
        except Exception as e:
            logger.error(f"❌ FTP connection failed: {e}")
            return None

    def download_file(self, ftp, remote_path, local_path):
        """Download a single file"""
        try:
            # Create local directory if it doesn't exist
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file already exists
            if local_path.exists():
                logger.debug(f"File already exists: {local_path.name}")
                return False
            
            # Download file
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {remote_path}', f.write)
            
            logger.info(f"✅ Downloaded: {local_path.name}")
            return True
        except Exception as e:
            logger.error(f"❌ Error downloading {remote_path}: {e}")
            return False

    def scan_and_download(self, days_back=2):
        """Scan FTP server and download new images"""
        ftp = self.connect_ftp()
        if not ftp:
            return 0
        
        downloaded_count = 0
        scanned_count = 0
        
        try:
            # Get current date in UTC
            now = datetime.utcnow()
            
            # Try specific dates that might have images
            # Based on your example: March 3rd, 2026
            test_dates = [
                datetime(2026, 3, 3),  # March 3, 2026
                datetime(2026, 3, 2),  # March 2, 2026
                datetime(2026, 3, 1),  # March 1, 2026
                datetime(2026, 2, 28), # February 28, 2026
            ]
            
            # Also check recent dates
            for i in range(days_back):
                date = now - timedelta(days=i)
                if date.year == 2026:  # Only check 2026
                    test_dates.append(date)
            
            # Remove duplicates
            test_dates = list(set(test_dates))
            test_dates.sort(reverse=True)
            
            for current_date in test_dates:
                year = current_date.strftime('%Y')
                month_num = current_date.strftime('%m')
                day = current_date.strftime('%d')
                
                # Get month name from number
                month_name = None
                for name, num in self.months.items():
                    if num == month_num:
                        month_name = name
                        break
                
                if not month_name or year != '2026':
                    continue
                
                logger.info(f"🔍 Checking: {year}/{month_name}/{day}")
                
                # Common time slots to check (every 30 minutes)
                time_slots = [f"{h:02d}{m:02d}" for h in range(0, 24) for m in (0, 30)]
                
                # Check each time slot
                for time_slot in time_slots:
                    # Construct the full remote path
                    # Format: /ELECTRO_L_3/2026/March/03/0115/260303_0115_original_RGB_VIS_IR.jpg
                    remote_dir = f"{self.base_path}{month_name}/{day}/{time_slot}/"
                    
                    try:
                        # Try to change to this directory
                        ftp.cwd(remote_dir)
                        
                        # List files in this directory
                        files = ftp.nlst()
                        
                        for filename in files:
                            # Check if it's the image we want
                            if filename.endswith('.jpg') and 'original_RGB_VIS_IR' in filename:
                                scanned_count += 1
                                
                                # Construct full remote path
                                remote_path = f"{remote_dir}{filename}"
                                
                                # Create local path: images/2026/03/03/filename
                                local_path = self.local_base / year / month_num / day / filename
                                
                                if self.download_file(ftp, remote_path, local_path):
                                    downloaded_count += 1
                    
                    except Exception as e:
                        # Directory doesn't exist or can't be accessed
                        continue
            
            logger.info(f"📊 Scan complete. Found: {scanned_count} matching files, Downloaded: {downloaded_count} new files")
            
            if scanned_count == 0:
                logger.warning("No matching images found. The FTP server structure might be different.")
                logger.info("Try checking manually with an FTP client to verify the path structure.")
                
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
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    downloader = SatelliteImageDownloader()
    downloader.scan_and_download(days_back=args.days)

if __name__ == "__main__":
    main()
