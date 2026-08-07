from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import textwrap
import os
from core.logger import get_logger

logger = get_logger("thumbnail_agent")

class ThumbnailAgent:
    """Generates branded thumbnail images for Instagram posts."""

    def __init__(self, output_dir: str = "output/thumbnails"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        title: str,
        subtitle: str = "",
        bg_color: tuple = (15, 15, 26),      # dark navy
        accent_color: tuple = (167, 139, 250), # violet
        text_color: tuple = (255, 255, 255),   # white
        size: tuple = (1080, 1080)             # Instagram square
    ) -> str:
        """
        Generate a branded thumbnail image.
        Returns the path to the saved PNG file.
        """
        logger.info(f"Generating thumbnail: '{title[:40]}'")

        img = Image.new("RGB", size, color=bg_color)
        draw = ImageDraw.Draw(img)

        width, height = size

        # Draw accent bar at top
        draw.rectangle([0, 0, width, 8], fill=accent_color)

        # Draw accent bar at bottom
        draw.rectangle([0, height-8, width, height], fill=accent_color)

        # Try to use a system font, fall back to default
        try:
            # Works on most systems — adjust path if needed
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
            label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except:
            # Fall back to default PIL font
            title_font = ImageFont.load_default()
            subtitle_font = title_font
            label_font = title_font

        # Draw "AI INSIGHTS" label at top
        label = "AI BUSINESS INSIGHTS"
        draw.text((60, 40), label, font=label_font, fill=accent_color)

        # Draw title (wrapped to fit)
        wrapped_title = textwrap.fill(title, width=20)
        title_y = height // 2 - 120

        # Draw title shadow for depth
        draw.text((62, title_y+2), wrapped_title, font=title_font, fill=(0,0,0,128))
        draw.text((60, title_y), wrapped_title, font=title_font, fill=text_color)

        # Draw subtitle
        if subtitle:
            subtitle_y = title_y + (wrapped_title.count('\n') + 1) * 80 + 20
            draw.text((60, subtitle_y), subtitle, font=subtitle_font, fill=accent_color)

        # Draw bottom label
        bottom_label = "Watch on YouTube →"
        draw.text((60, height - 80), bottom_label, font=label_font, fill=(180,180,180))

        # Save
        safe_title = "".join(c for c in title[:30] if c.isalnum() or c in " _-").strip()
        filename = f"thumbnail_{safe_title.replace(' ', '_')}.png"
        output_path = self.output_dir / filename
        img.save(str(output_path), "PNG", quality=95)

        logger.info(f"Thumbnail saved: {output_path}")
        return str(output_path)