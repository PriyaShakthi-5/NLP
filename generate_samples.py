from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

samples = [
    ("prescription_1.jpg", "Sample Prescription\nPatient: John Doe\nMedicine: Paracetamol\nDosage: 1 tablet\nFrequency: 2x daily\nDuration: 5 days"),
    ("prescription_2.jpg", "Sample Prescription\nPatient: Jane Smith\nMedicine: Amoxicillin\nDosage: 2 capsules\nFrequency: 3x daily\nDuration: 7 days"),
    ("prescription_3.jpg", "Sample Prescription\nPatient: Bob Johnson\nMedicine: Cetirizine\nDosage: 1 tablet\nFrequency: 1x daily\nDuration: 10 days"),
]

output_dir = Path(__file__).resolve().parent
upload_dir = output_dir / 'uploads'
upload_dir.mkdir(exist_ok=True)

for filename, text in samples:
    img = Image.new('RGB', (900, 1200), 'white')
    draw = ImageDraw.Draw(img)
    draw.rectangle((40, 40, 860, 1160), outline='black', width=4)
    try:
        font_title = ImageFont.truetype("arial.ttf", 60)
        font_text = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font_title = None
        font_text = None

    draw.text((80, 120), 'Prescription', fill='navy', font=font_title)
    y = 220
    for line in text.splitlines():
        draw.text((80, y), line, fill='black', font=font_text)
        y += 80
    img.save(output_dir / filename)
    img.save(upload_dir / filename)
    print(f'{filename} created')
