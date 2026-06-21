"""
GC9A01 240x240 round display driver for Raspberry Pi via framebuffer.
Uses kernel device tree overlay (dtoverlay=gc9a01) which creates /dev/fb1.
"""

import logging
import mmap
import os
import struct

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

try:
    FRAMEBUFFER_PATH = "/dev/fb1"
    HARDWARE_AVAILABLE = os.path.exists(FRAMEBUFFER_PATH)
except Exception:
    HARDWARE_AVAILABLE = False
    logger.warning("Could not check /dev/fb1. Enable dtoverlay=gc9a01 in /boot/config.txt and reboot.")


class DisplayDriver:
    """GC9A01 display driver using framebuffer (/dev/fb1)."""
    
    def __init__(self):
        self.width = 240
        self.height = 240
        self.fb_path = FRAMEBUFFER_PATH
        self.fb_file = None
        self.fb_mmap = None
        self.fb_size = self.width * self.height * 2  # RGB565 = 2 bytes per pixel
        self.mock_mode = not HARDWARE_AVAILABLE
        self.image = None
        self.draw = None
        self.font = None
        self.font_bold = None
        self.buffer = None  # Double buffer
        
    def init(self):
        """Initialize the display."""
        # Initialize fonts even in mock mode
        try:
            self.font = ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf', 10)
            self.font_bold = ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf', 10)
        except:
            try:
                self.font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 10)
                self.font_bold = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 10)
            except:
                try:
                    self.font = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', 10)
                    self.font_bold = ImageFont.truetype('/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf', 10)
                except:
                    self.font = ImageFont.load_default()
                    self.font_bold = self.font

        if self.mock_mode:
            logger.info("Mock display initialized (240x240)")
            return

        try:
            # Open framebuffer device
            self.fb_file = open(self.fb_path, 'r+b')
            # Map to memory
            self.fb_mmap = mmap.mmap(self.fb_file.fileno(), self.fb_size)
            logger.info("Framebuffer initialized: %dx%d at %s", self.width, self.height, self.fb_path)
            
            # Initialize PIL image for drawing (double buffer)
            self.image = Image.new('RGB', (self.width, self.height))
            self.buffer = Image.new('RGB', (self.width, self.height))
            self.draw = ImageDraw.Draw(self.image)

            # Clear display
            self.clear()
        except Exception as e:
            logger.error("Error initializing framebuffer: %s", e)
            self.mock_mode = True
        
    def clear(self):
        """Clear the display to black."""
        if self.mock_mode:
            return
        self.draw.rectangle((0, 0, self.width, self.height), fill=(0, 0, 0))
        self._sync_framebuffer()
    
    def save_buffer(self):
        """Save current image to buffer."""
        if self.mock_mode or not self.buffer:
            return
        self.buffer.paste(self.image)
    
    def restore_buffer(self):
        """Restore image from buffer."""
        if self.mock_mode or not self.buffer:
            return
        self.image.paste(self.buffer)
        self.draw = ImageDraw.Draw(self.image)
        
    def _sync_framebuffer(self):
        """Sync PIL image to framebuffer."""
        if self.mock_mode or not self.fb_mmap:
            return
        # Convert RGB to RGB565 and write to framebuffer
        rgb_data = self.image.tobytes()
        rgb565_data = bytearray(self.fb_size)
        for i in range(0, len(rgb_data), 3):
            r, g, b = rgb_data[i:i+3]
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            rgb565_data[i*2//3:i*2//3+2] = struct.pack('<H', rgb565)
        self.fb_mmap[:] = rgb565_data
        
    def fill(self, color):
        """Fill display with color (RGB565)."""
        if self.mock_mode:
            return
        # Convert RGB565 to RGB tuple
        r = ((color >> 11) & 0x1F) << 3
        g = ((color >> 5) & 0x3F) << 2
        b = (color & 0x1F) << 3
        self.draw.rectangle((0, 0, self.width, self.height), fill=(r, g, b))
        self._sync_framebuffer()
        
    def color565(self, r, g, b):
        """Convert RGB to RGB565."""
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    
    def _rgb565_to_rgb(self, color):
        """Convert RGB565 to RGB tuple."""
        r = ((color >> 11) & 0x1F) << 3
        g = ((color >> 5) & 0x3F) << 2
        b = (color & 0x1F) << 3
        return (r, g, b)
        
    def pixel(self, x, y, color):
        """Draw a single pixel."""
        if self.mock_mode:
            return
        rgb = self._rgb565_to_rgb(color)
        self.draw.point((x, y), fill=rgb)
        
    def line(self, x0, y0, x1, y1, color, width=1):
        """Draw a line."""
        if self.mock_mode:
            return
        rgb = self._rgb565_to_rgb(color)
        self.draw.line((x0, y0, x1, y1), fill=rgb, width=width)
        
    def circle(self, x, y, radius, color, width=1):
        """Draw a circle outline."""
        if self.mock_mode:
            return
        rgb = self._rgb565_to_rgb(color)
        self.draw.ellipse((x-radius, y-radius, x+radius, y+radius), outline=rgb, width=width)
        
    def fill_circle(self, x, y, radius, color):
        """Draw a filled circle."""
        if self.mock_mode:
            return
        rgb = self._rgb565_to_rgb(color)
        self.draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=rgb)
        
    def triangle(self, x0, y0, x1, y1, x2, y2, color):
        """Draw a filled triangle."""
        if self.mock_mode:
            return
        rgb = self._rgb565_to_rgb(color)
        self.draw.polygon([(x0, y0), (x1, y1), (x2, y2)], fill=rgb)
        
    def text(self, text, x, y, color, font=None):
        """Draw text at position."""
        if self.mock_mode:
            return
        rgb = self._rgb565_to_rgb(color)
        font_to_use = font if font else self.font
        self.draw.text((x, y), text, fill=rgb, font=font_to_use)
    
    def rect(self, x, y, width, height, color, fill=None):
        """Draw a rectangle."""
        if self.mock_mode:
            return
        rgb = self._rgb565_to_rgb(color)
        fill_rgb = self._rgb565_to_rgb(fill) if fill else None
        self.draw.rectangle((x, y, x+width, y+height), outline=rgb, fill=fill_rgb)
    
    def show(self):
        """Sync the PIL image to the framebuffer."""
        self._sync_framebuffer()
