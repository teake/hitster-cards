from collections import Counter
from xml.etree import ElementTree

import qrcode
import qrcode.image.svg
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def generate_year_distribution_pdf(release_dates: list[str], output_pdf: str) -> None:
    year_counts = Counter(int(release_date[:4]) for release_date in release_dates)

    min_year = min(year_counts.keys())
    max_year = max(year_counts.keys())
    all_years = list(range(min_year, max_year + 1))
    counts = [year_counts.get(year, 0) for year in all_years]

    plt.figure()
    plt.bar(all_years, counts, color="black")
    plt.ylabel("number of songs released")
    plt.xticks()

    with PdfPages(output_pdf) as pdf:
        pdf.savefig()
        plt.close()

def generate_qr_code(qr_content: str) -> str:
    img = qrcode.make(qr_content, image_factory=qrcode.image.svg.SvgPathImage)
    return ElementTree.tostring(img.get_image()).decode()