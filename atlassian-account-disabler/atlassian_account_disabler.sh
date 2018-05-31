#!/bin/bash

user_names=(accounts...)
for i in ${user_names[@]}; do
        jira.sh --action updateUser --userId "$i" --deactivate \
        --server "https:// + the atlassian account URL (the regular one you login with)" \
        --password "password" --user "username"
done
