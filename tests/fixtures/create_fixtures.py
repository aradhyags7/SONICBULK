"""Generate test fixtures for PDF, DOCX, CSV, and text."""

from pathlib import Path

import docx
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

FIXTURES_DIR = Path(__file__).parent

MESSY_TEXT = """
1. Queen - Bohemian Rhapsody (Official Video) [HD] 05:55
#2) The Beatles - Hey Jude (Remastered 2015) 120 bpm
3. "Imagine" by John Lennon https://youtube.com/watch?v=123
• Michael Jackson - Billie Jean [Audio] 117 BPM
▫ AC/DC: Back in Black (Official Music Video)
6. Drake feat. Rihanna - Take Care (Visualizer) 4:37
7. Ed Sheeran - Shape of You [Lyrics Video] 🔥🎵
8 - Adele - Rolling in the Deep (Live at the Royal Albert Hall)
9. Pink Floyd - Comfortably Numb
10. Hotel California by Eagles
11. Queen - Bohemian Rhapsody  # Duplicate
12. Queen - Bohemian Rhapsody (Lyric Video)  # Near-duplicate
"""

def create_text_fixture() -> None:
    path = FIXTURES_DIR / "messy_songs.txt"
    path.write_text(MESSY_TEXT.strip(), encoding="utf-8")

def create_csv_fixture() -> None:
    path = FIXTURES_DIR / "songs.csv"
    csv_content = """Artist,Title,Album
Queen,Bohemian Rhapsody,A Night at the Opera
Daft Punk,Get Lucky,Random Access Memories
Nirvana,Smells Like Teen Spirit,Nevermind
Eminem feat. Rihanna,Love the Way You Lie,Recovery
The Weeknd,Blinding Lights,After Hours
"""
    path.write_text(csv_content.strip(), encoding="utf-8")

def create_docx_fixture() -> None:
    path = FIXTURES_DIR / "songs.docx"
    doc = docx.Document()
    doc.add_heading("My Playlist", level=1)
    doc.add_paragraph("1. Queen - Bohemian Rhapsody (Official Video)")
    doc.add_paragraph("2. The Beatles - Hey Jude [Lyrics]")
    doc.add_paragraph("3. Imagine by John Lennon")

    table = doc.add_table(rows=1, cols=2)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Artist"
    hdr_cells[1].text = "Title"

    row1 = table.add_row().cells
    row1[0].text = "Daft Punk"
    row1[1].text = "Around the World"

    row2 = table.add_row().cells
    row2[0].text = "Radiohead"
    row2[1].text = "Karma Police"

    doc.save(str(path))

def create_pdf_fixtures() -> None:
    # 1. Standard single column PDF with page numbers
    pdf_path = FIXTURES_DIR / "standard_songs.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 750, "Header: Playlist 2024")
    c.drawString(100, 700, "1. Queen - Bohemian Rhapsody (Official Video)")
    c.drawString(100, 670, "2. Pink Floyd - Wish You Were Here")
    c.drawString(100, 640, "3. Led Zeppelin - Stairway to Heaven")
    c.drawString(100, 610, "4. Billie Jean by Michael Jackson")
    c.drawString(100, 50, "Page 1 of 1")
    c.save()

    # 2. Two-column PDF
    two_col_path = FIXTURES_DIR / "two_column_songs.pdf"
    c2 = canvas.Canvas(str(two_col_path), pagesize=letter)
    # Left column (x=50..250)
    c2.drawString(50, 700, "1. Queen - Bohemian Rhapsody")
    c2.drawString(50, 670, "2. The Beatles - Let It Be")
    c2.drawString(50, 640, "3. Nirvana - Come As You Are")
    # Right column (x=350..550)
    c2.drawString(350, 700, "4. Radiohead - Creep")
    c2.drawString(350, 670, "5. Oasis - Wonderwall")
    c2.drawString(350, 640, "6. Blur - Song 2")
    c2.save()

    # 3. Scanned PDF (empty text layer)
    scanned_path = FIXTURES_DIR / "scanned_empty.pdf"
    c3 = canvas.Canvas(str(scanned_path), pagesize=letter)
    # Draw a rectangle / graphic but NO text
    c3.rect(100, 100, 400, 500, stroke=1, fill=0)
    c3.save()

if __name__ == "__main__":
    create_text_fixture()
    create_csv_fixture()
    create_docx_fixture()
    create_pdf_fixtures()
    print("Fixtures created successfully.")
