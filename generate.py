"""
Simple QR Code Generator for any website.

Install the required library first:
    pip install qrcode[pil]

Run:
    python qr_generator.py
"""

import qrcode


def create_qr(url, filename="qrcode.png"):
    # Add https:// if the user forgot it
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    qr = qrcode.QRCode(
        version=None,        # auto-pick the smallest size that fits
        box_size=10,         # normal size: each box is 10 pixels
        border=4,            # standard quiet-zone border
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)
    print(f"QR code for {url} saved as {filename}")


if __name__ == "__main__":
    website = input("Enter website URL: ").strip()
    create_qr(website)