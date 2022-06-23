#!/usr/bin/env python3

import sys
import csv

input=sys.argv[1]
output=sys.argv[2]

def transform_uppercase(input, output):
    out = []
    print("Reading input...")
    # open file in read mode
    with open(input, 'r', encoding='utf-8') as input_file:
        # pass file object to reader() to get reader object
        csv_reader = csv.DictReader(input_file)
        print("Transforming rows...")       
        # Iterate over each row in the csv using reader object
        for row in csv_reader:
            # row variable is a list that represents a row in csv
            row["FirstName"] = row["FirstName"].upper()
            row["LastName"] = row["LastName"].upper()
            out.append(row)
        input_file.close()
    print("Saving output...")
    keys = out[0].keys()
    with open(output, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(out)
        output_file.close()
    print("Finished writing results")

transform_uppercase(input,output)
