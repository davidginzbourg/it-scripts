html_email = """
    <html>
    <head>
        <style>
            table,p {{
                font-family: 'Trebuchet MS', Arial, Helvetica, sans-serif;
                border-collapse: collapse;
                width: 100%;
            }}

            table td, #customers th {{
                border: 1px solid #ddd;
                padding: 8px;
            }}

            table tr:nth-child(even){{background-color: #eeeeee;}}

            table tr:hover {{background-color: #ddd;}}

            table th {{
                padding: 8px;
                text-align: left;
                background-color: #c6c6c6;
                color: black;
            }}
        </style>
    </head>
    <body>
    {}
    </body>
    </html>
    """
p = "<p>{}</p><br>"
depl_table = """
    <table>
    <tr>
        <th>Deployment ID</th>
        <th>Customer Name</th>
        <th>Created At</th>
        <th>Updated At</th>
    </tr>
    {}
    </table>
    <br>
    """
depl_cell = "<tr><td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td></tr>"
