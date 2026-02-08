"""
MOSDAC Image Downloader
"""
import asyncio
import aiohttp
import aiofiles
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin
from typing import List, Dict, Optional
import yaml

class MOSDACDownloader:
    def __init__(self, config: dict):
        self.config = config
        self.base_url = config['mosdac']['base_url']
        self.product_json_url = config['mosdac']['product_json_url']
        self.api_endpoint = config['mosdac']['api_endpoint']
        self.logger = logging.getLogger(__name__)
        
        # Create base directory
        self.base_dir = Path(config['storage']['base_dir'])
        self.base_dir.mkdir(exist_ok=True)
        
        # Product catalog cache
        self.product_catalog = None
        
    async def fetch_product_catalog(self) -> List[Dict]:
        """Fetch and parse the product catalog JSON"""
        self.logger.info("Fetching product catalog...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.product_json_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.product_catalog = data
                        return data
                    else:
                        self.logger.error(f"Failed to fetch catalog: {response.status}")
                        return []
        except Exception as e:
            self.logger.error(f"Error fetching catalog: {e}")
            return []
    
    async def get_image_list(self, pattern: str, date_str: str) -> List[str]:
        """Get list of images for a specific pattern and date"""
        payload = {
            "prod": pattern,
            "st_date": date_str,
            "count": str(self.config['download']['count_per_request'])
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Accept': 'application/json, text/plain, */*',
                    'Content-Type': 'application/json;charset=UTF-8',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                async with session.post(
                    self.api_endpoint,
                    json=payload,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if isinstance(result, list) and len(result) > 0:
                            # Parse the response string
                            image_list_str = result[0]
                            if image_list_str:
                                images = image_list_str.split(',')
                                # Clean up the paths
                                cleaned_images = []
                                for img in images:
                                    if img.strip():
                                        # Remove any trailing commas or quotes
                                        img = img.strip().strip('"').strip("'")
                                        cleaned_images.append(img)
                                return cleaned_images
        except Exception as e:
            self.logger.error(f"Error fetching image list for {pattern}: {e}")
        
        return []
    
    async def download_image(self, session: aiohttp.ClientSession, 
                           image_path: str, save_path: Path) -> bool:
        """Download a single image"""
        image_url = urljoin(self.base_url, f"/look/{image_path}")
        
        try:
            async with session.get(image_url) as response:
                if response.status == 200:
                    # Create directory if it doesn't exist
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Save the image
                    async with aiofiles.open(save_path, 'wb') as f:
                        await f.write(await response.read())
                    
                    self.logger.debug(f"Downloaded: {save_path}")
                    return True
                else:
                    self.logger.warning(f"Failed to download {image_url}: {response.status}")
                    return False
        except Exception as e:
            self.logger.error(f"Error downloading {image_url}: {e}")
            return False
    
    def get_save_path(self, image_path: str, satellite: str, 
                     sensor: str, product_type: str) -> Path:
        """Generate save path based on organization rules"""
        # Extract date from image path
        # Example: 3S_IMG/preview/2026/08FEB/3SIMG_08FEB2026_1800_L1B_STD_IR1_V01R00.jpg
        parts = image_path.split('/')
        
        # Try to extract date information
        date_parts = []
        for part in parts:
            if part.isdigit() and len(part) == 4:  # Year
                date_parts.append(part)
            elif len(part) == 5 and part[:2].isdigit() and part[2:].isalpha():  # 08FEB
                date_parts.append(part)
        
        # Build path based on organization rules
        path_parts = [self.base_dir]
        
        for org in self.config['storage']['organize_by']:
            if org == 'satellite':
                path_parts.append(satellite.replace('/', '_'))
            elif org == 'sensor':
                path_parts.append(sensor.replace('/', '_'))
            elif org == 'product_type':
                path_parts.append(product_type.replace('/', '_'))
            elif org == 'date' and date_parts:
                path_parts.extend(date_parts)
        
        # Add filename
        filename = parts[-1] if parts else f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        path_parts.append(filename)
        
        return Path(*path_parts)
    
    async def download_all_images(self, start_date: datetime, end_date: datetime):
        """Download all images within date range"""
        # Fetch product catalog
        catalog = await self.fetch_product_catalog()
        if not catalog:
            self.logger.error("No product catalog available")
            return
        
        # Prepare date range
        current_date = start_date
        date_strings = []
        
        while current_date <= end_date:
            date_strings.append(current_date.strftime('%Y-%m-%d'))
            current_date += timedelta(days=1)
        
        # Apply filters
        satellites_filter = self.config['filters']['satellites']
        sensors_filter = self.config['filters']['sensors']
        product_types_filter = self.config['filters']['product_types']
        
        semaphore = asyncio.Semaphore(self.config['download']['max_concurrent'])
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            
            for satellite_data in catalog:
                satellite_name = satellite_data['sat']
                
                # Apply satellite filter
                if satellites_filter and satellite_name not in satellites_filter:
                    continue
                
                for sensor_data in satellite_data['sensor']:
                    sensor_name = sensor_data['sen']
                    
                    # Apply sensor filter
                    if sensors_filter and sensor_name not in sensors_filter:
                        continue
                    
                    for type_data in sensor_data['type']:
                        product_type = type_data['prodt']
                        
                        # Apply product type filter
                        if product_types_filter and product_type not in product_types_filter:
                            continue
                        
                        for product in type_data['prodlist']:
                            pattern = product['pat']
                            product_name = product['prod']
                            
                            self.logger.info(f"Processing: {satellite_name}/{sensor_name}/{product_type}/{product_name}")
                            
                            # Get images for each date
                            for date_str in date_strings:
                                image_list = await self.get_image_list(pattern, date_str)
                                
                                for image_path in image_list:
                                    save_path = self.get_save_path(
                                        image_path, satellite_name, 
                                        sensor_name, product_type
                                    )
                                    
                                    # Check if file already exists
                                    if save_path.exists():
                                        self.logger.debug(f"Skipping existing: {save_path}")
                                        continue
                                    
                                    # Create download task with semaphore
                                    task = self._download_with_semaphore(
                                        semaphore, session, image_path, save_path
                                    )
                                    tasks.append(task)
            
            # Run all downloads concurrently
            if tasks:
                self.logger.info(f"Starting {len(tasks)} downloads...")
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Count successful downloads
                successful = sum(1 for r in results if r is True)
                failed = sum(1 for r in results if r is False)
                
                self.logger.info(f"Download complete: {successful} successful, {failed} failed")
            else:
                self.logger.info("No new images to download")
    
    async def _download_with_semaphore(self, semaphore, session, image_path, save_path):
        """Download with semaphore for rate limiting"""
        async with semaphore:
            return await self.download_image(session, image_path, save_path)
    
    async def download_latest_only(self):
        """Download only the latest images (for frequent updates)"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)  # Last 24 hours
        
        await self.download_all_images(start_date, end_date)
