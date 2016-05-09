#!/bin/bash

self="${0##*/}"
lambda="elbattachment.py"
timestamp=$(date --utc +%FT%H%M%SZ)
archive="/tmp/elbattachment-${timestamp}.zip"

pip install -t . requests boto3 cfn-response

zip -q -x $self -r $archive *

for file in *; do [[ "$file" = "$self" || "$file" = "$lambda" ]] || rm -fr "$file"; done

echo "Created $archive"
