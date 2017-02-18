try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup
lines = []
with open('/home/david/Downloads/cloudify_ps.html', 'r') as f:
    for line in f:
        lines.append(line)

html = ''.join(lines)
parsed_html = BeautifulSoup(html, 'html.parser')
# print parsed_html.body.find('div', attrs={'class':'container'}).text
users = []
for i in parsed_html('a', attrs={'class': 'css-truncate-target f4'}):
    print(i.text.strip())