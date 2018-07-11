msg_html = """
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
action_table = """
    <table>
    <tr><th>Instance</th><th>Action status</th></tr>
    {}
    </table>
    <br>
    """
action_table_cell_format = "<tr><td>{0}</td><td>{1}</td></tr>"
warning_table = """
    <table>
    <tr><th>Instance</th></tr>
    {}
    </table>
    <br>
    """
warning_table_cell_format = "<tr><td>{0}</td></tr>"
