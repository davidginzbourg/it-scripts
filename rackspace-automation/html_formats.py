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
    <tr><th>Instance</th><th>Action status</th><th>Reason</th></tr>
    {}
    </table>
    <br>
    """
action_table_cell_format = "<tr><td>{0}</td><td>{1}</td><td>{2}</td></tr>"
warning_table = """
    <table>
    <tr><th>Instance</th><th>Note</th></tr>
    {}
    </table>
    <br>
    """
warning_table_cell_format = "<tr><td>{0}</td><td>{1}</td></tr>"
global_action_table = """
    <table>
    <tr>
    <th>Tenant</th><th>Instance</th><th>Action status</th><th>Reason</th>
    </tr>
    {}
    </table>
    <br>
    """
global_action_table_cell_format = "<tr>" \
                                  "<td>{0}</td><td>{1}</td><td>{2}</td>" \
                                  "<td>{3}</td>" \
                                  "</tr>"
global_warning_table = """
    <table>
    <tr><th>Tenant</th><th>Instance</th><th>Note</th></tr>
    {}
    </table>
    <br>
    """
global_warning_table_cell_format = "<tr><td>{0}</td><td>{1}</td><td>{2}</td>" \
                                   "</tr>"
action_msg_fmt = 'The instance was in the {0} state for more than {1} days.'
shlv_wrn_msg_fmt = "Will be shelved in {0} days. Maximum time" \
                   " allowed in the {1} state is {2} days."
del_wrn_msg_fmt = "Will be deleted in {0} days. Maximum time" \
                  " allowed in the {1} state is {2} days."
