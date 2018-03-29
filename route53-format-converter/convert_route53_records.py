import json

INPUT = 'path to source'
OUTPUT = 'path to output'
OLD_HOSTED_ZONE_ID = '_'
NEW_HOSTED_ZONE_ID = '_'
MAX_NUM_OF_RECORDS = 999

def output_to_file(out_dict, path):
	with open(path, 'w') as f:
		json.dump(out_dict, f)

with open(INPUT, 'r') as f:
	route53_file = json.load(f)

route53_file['ResourceRecordSets'] = filter(
	lambda x: 'SOA' not in x['Type'] and 'NS' not in x['Type'],
	route53_file['ResourceRecordSets'])

part = 0
record_cnt = 0
out_dict = {'Changes':[]}
for record_set in route53_file['ResourceRecordSets']:
	if record_cnt >= MAX_NUM_OF_RECORDS:
		output_to_file(out_dict, OUTPUT + '_part_' + part)
		part += 1
		record_cnt = 0
		out_dict = {'Changes':[]}

	if 'AliasTarget' not in record_set:
		out_dict['Changes'].append({'Action': 'CREATE', 'ResourceRecordSet':record_set})
	record_cnt += 1

for record_set in route53_file['ResourceRecordSets']:
	if record_cnt >= MAX_NUM_OF_RECORDS:
		output_to_file(out_dict, OUTPUT + '_part_' + part)
		part += 1
		record_cnt = 0
		out_dict = {'Changes':[]}

	if 'AliasTarget' in record_set:
		if 'HostedZoneId' in record_set['AliasTarget'] \
			and OLD_HOSTED_ZONE_ID == record_set['AliasTarget']['HostedZoneId']:
			record_set['AliasTarget']['HostedZoneId'] = NEW_HOSTED_ZONE_ID
		out_dict['Changes'].append({'Action': 'CREATE', 'ResourceRecordSet':record_set})
	record_cnt += 1

# If the file was divided
if part > 1:
	output_to_file(out_dict, OUTPUT + '_part_' + part)
else:
	output_to_file(out_dict, OUTPUT)