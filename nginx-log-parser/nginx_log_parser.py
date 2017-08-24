import re
import sys
import datetime

content = []
with open(sys.argv[1], 'r') as f:
    for line in f:
        content.append(line)

init_output = {}
for line in content:
    path_matcher = re.search('"([^"]+)"', line)
    path_match = path_matcher.group(1) if path_matcher else 'Unknown'
    path_refined_matcher = re.search('\w+\s([^ ]+)\s+?', path_match)
    path = path_refined_matcher.group(1) if path_refined_matcher else 'Unknown'
    ip_matcher = re.search('(\d{1,3}([.]\d{1,3})+){1}', line)
    ip = ip_matcher.group(0) if ip_matcher else 'Unknown'
    time_matcher = re.search('\[(.+?)\]', line)
    t = time_matcher.group(1) if time_matcher else '01/Jan/1970:00:00:00'
    time_instance = datetime.datetime.strptime(re.sub('\s(\+|-)\d{4}', '', t),
                                               '%d/%b/%Y:%H:%M:%S')
    time_str = time_instance.strftime('%m/%d/%Y')
    if (time_str, path, ip) in init_output:
        init_output[(time_str, path, ip)] += 1
    else:
        init_output[(time_str, path, ip)] = 1

output = map(lambda x: (x[0][0], x[0][1], x[0][2], x[1]), sorted(
    init_output.items(),
    key=lambda i: (
        datetime.datetime.strptime(i[0][0], '%m/%d/%Y'),
        i[0][1],
        i[0][2])))
with open(sys.argv[2], 'w') as f:
    for item in output:
        f.write('{0},{1},{2},{3}\n'.format(item[0], item[1], item[2], item[3]))
