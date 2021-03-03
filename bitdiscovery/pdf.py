import os
from datetime import datetime
from typing import List, Dict, Any, Tuple
from fpdf import FPDF, HTMLMixin


class HTML2PDF(FPDF, HTMLMixin):
    pass


class PdfPage:
    """
    A page of a pdf, which holds the necessary data: the key, the name and the description of the page.
    """
    key: str
    title: str
    description: str

    def __init__(self, key: str, title: str, description: str):
        self.key = key
        self.title = title
        self.description = description


class PdfBuilder:
    """
    Initializes an HTML2PDF object to create pages to a Bit Discovery report.
    """
    pdf: HTML2PDF
    title: str
    resource_directory: str

    def __init__(self, title: str, resource_directory: str):
        self.pdf = HTML2PDF('P', 'mm', 'A4')
        self.pdf.set_auto_page_break(0, margin=0.0)
        self.title = title
        self.resource_directory = resource_directory
        self.pdf.add_font('Avenir Book', fname=self.get_resource('avenir-book.ttf'), uni=True)
        self.pdf.add_font('Avenir Black', fname=self.get_resource('avenir-black.ttf'), uni=True)

    def get_resource(self, res: str) -> str:
        return os.path.join(self.resource_directory, res)

    def add_title_page(self):
        """
        Add the title page with the PDF Builder name.
        """
        self.pdf.add_page()
        self.pdf.set_line_width(0)
        self.pdf.set_fill_color(153, 30, 50)
        self.pdf.rect(0, 0, 210, 297, 'DF')
        self.pdf.set_font('Avenir Book', '', 29)
        self.pdf.set_text_color(230, 199, 204)
        self.pdf.text(30, 80, txt='Bit Discovery Asset Inventory')
        self.pdf.set_font('Avenir Book', '', 46)
        self.pdf.set_text_color(255, 255, 255)
        self.pdf.text(30, 100, txt=str(self.title)[:20])

        self.pdf.set_font('Avenir Book', '', 18)
        self.pdf.image(self.get_resource('footer-img.png'), 0, 180, 240)
        self.pdf.image(self.get_resource('bd2020logowhite.png'), 166, 278, 33)
        self.pdf.set_text_color(230, 199, 204)
        self.pdf.cell(0, 315, txt=str(datetime.now().strftime('%B %Y')), align='R')

    def add_count_page(self, name: str, description: str, count: int):
        """
        Add page where the count of some value is displayed.

        :param name: the name of the counted object.
        :param description: the description of the counted object, displayed at .
        :param count: the count of the object.
        """
        Name = name.capitalize()
        self.pdf.add_page()
        self.pdf.set_font('Avenir Book', '', 29)
        self.pdf.set_text_color(0, 0, 0)
        self.pdf.text(10, 20, txt=f'Total {Name}s')
        self.pdf.set_font('Avenir Book', '', 11)
        self.pdf.text(10, 30, txt=f"The total number of {name}s accross all of {self.title}'s domain names.")
        self.pdf.set_font('Avenir Black', '', 75)
        self.pdf.multi_cell(200, 250, txt=str("{:,}".format(count)), align='C')

        self.pdf.set_font('Avenir Book', '', 46)
        if count == 1:
            self.pdf.multi_cell(200, -200, txt=Name, align='C')
        else:
            self.pdf.multi_cell(200, -200, txt=f'{Name}s', align='C')
        html = f"""
                <br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br>
                <p><font face='Helvetica' size=11><b>Asset Definition</b></font></p>
                <p><font face='Helvetica' size=11>{description}</font></p>
                """
        self.pdf.write_html(html)

    def add_graph_page(self, page: PdfPage, data: List[Dict[str, Any]], image: str, totalsize: int):
        """
        Add analysing page with an image and a table.

        :param page: PdfPage object which holds the necessary key, title and description.
        :param data: the data to show as a table (as a dictionary with name and value keys)
        :param image: the URL of an image (should be relative to the resource directory).
        :param totalsize: the total number of assets.
        """
        self.pdf.add_page()
        self.pdf.set_text_color(44, 56, 69)
        self.pdf.set_font('Avenir Book', '', 29)
        self.pdf.text(10, 20, txt=page.title)
        description = f"<br><br><p><font face='Helvetica' size=11>{page.description}</font></p><br>"
        self.pdf.write_html(description)
        table = f"""
                <font face="Helvetica" size=11><table width="100%" border="1" align="center">
                    <thead>
                        <tr>
                            <th bgcolor="#F3F4F5" width="70%">{page.title}</th>
                            <th bgcolor="#F3F4F5" width="15%">Count</th>
                            <th bgcolor="#F3F4F5" width="15%">Percent</th>
                        </tr>
                    </thead>
                    <tbody>
                """

        if len(data) > 0:
            missingrow: Dict[str, Any] = {}
            foundmissing: bool = False
            empty: int = 0
            rows: List[Tuple[str, int]] = []

            for row in data:
                if str(row['name']) == "__missing__":
                    missingrow = row
                    foundmissing = True
                else:
                    if str(row['name']) == '':
                        # Fixes a UI bug with how the table is rendered
                        empty = int(row['value'])
                        foundmissing = True
                        continue

                    rows.append((str(row['name']), int(row['value'])))

            # If there is a missing row, add its value to the end
            if foundmissing:
                rows.append((str(missingrow['name']), int(missingrow['value'] + empty)))

            if not foundmissing and empty > 0:
                rows.append(("__missing__", empty))

            # Generate rows
            for (i, (name, value)) in enumerate(rows):
                # Truncate long strings, and calculate percentage
                name = name[:75] + '...' if len(name) > 75 else name
                percent = round((float(value) / float(totalsize)) * 100, 2)
                # Add row to the table
                if i % 2 == 0:
                    table += f"<tr><td>{name}</td><td>{str(value)}</td><td>{str(percent)}%</td></tr>"
                else:
                    table += f"<tr><td bgcolor='#f0fafa'>{name}</td><td bgcolor='#f0fafa'>{str(value)}</td><td bgcolor='#f0fafa'>{str(percent)}%</td></tr>"

            table += "</tbody></table></font>"

        else:
            table = '<font face="Helvetica" size=11>No data found.</font>'

        self.pdf.image(self.get_resource(image), w=180)
        # self.pdf.write_html('<center><font face="Helvetica" size=10>Assets by ' + str(page.title) + '</font></center>')
        self.pdf.write_html(table)
        self.pdf.image(self.get_resource('bd2020logoblue.png'), 166, 278, 33)

    def save(self, filename: str):
        """
        Save the pdf file to a path.

        :param filename: The filename to save to (should be relative to the resource directory).
        :return:
        """
        self.pdf.output(self.get_resource(filename), 'F')
