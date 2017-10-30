#!/usr/bin/env python3

import os
import re
from  optparse import OptionParser
from executable import Executable
from job import Job

JOBS         = {}
EXECUTABLES  = {}
EXTERNAL_IN  = {}
EXTERNAL_OUT = {}

def parse_args():

  parser = OptionParser(usage="%prog -i dag_file")

  parser.add_option("-i", "--input", dest="dag_file", action="store",
                    type="string", default="",
                    help="Pegasus dag file")


  (options, args) = parser.parse_args()

  if not options.dag_file:
    print("Input file required")
    exit(-1)

  return options  

def check_format(dag):
  while True:
    line = dag.readline()

    if line.startswith("<adag"):
      return True
    elif line == "":
      return False

def main():
  options  = parse_args()
  elements = { "<job"      : parse_job,
               "<child"    : parse_deps,                  
               "<filename" : parse_input}

  if not os.path.exists(options.dag_file):
    print("Input file does not exist")
    exit(-1)
  
  with open(options.dag_file, "r") as dag:
    if not check_format(dag):
      print("Input file is not in dag format")
      exit(-1)

    line = ""
    while not line.strip().startswith("</adag>"):
      line = dag.readline()
      if not line: break

      if len(line.split()) > 0:
        tag  = line.split()[0]
      
        if tag in elements:
          elements[tag](line, dag)


  resolve_names()
  write_output()


def parse_job(head, dag):
  xml_body   = []
  regex      = re.compile('.*id="([^"]*)" name="([^"]*)".*dv-name="([^"]*)".*>')
  match      = regex.match(head.strip())
  job_id     = match.group(1)
  executable = match.group(2)
  name       = match.group(3) 
 
  line = dag.readline()

  while not "</job>" in line:
    xml_body.append(line.strip())
    line = dag.readline()

  if not executable in EXECUTABLES:
    EXECUTABLES[executable] = Executable(executable, xml_body)

  JOBS[job_id] = Job(name, EXECUTABLES[executable], xml_body)
        
       

def parse_deps(head, dag):
  xml_body = []
  parents  = []
  job_id   = head.split('"')[1]
 
  line = dag.readline()

  while not "</child>" in line:
    if not line: break
    if "parent" in line: parents.append(line.split('"')[1])
    line = dag.readline()    

  for parent in parents:
    for inp in JOBS[job_id].inputs.values():
      for name, out in JOBS[parent].outputs.items():
        if inp['value'] ==  out['value']:
          inp['link'] = JOBS[parent].name + "/" + name


def parse_input(head, dag):
  regex  = re.compile('.*file="([^"]*)".*link="([^"]*)".*/>')
  match  = regex.match(head.strip())
  f_name = match.group(1)
  direct = match.group(2)

  if (direct == "input"):
    EXTERNAL_IN[f_name] = {"name": "ext_input_" + str(len(EXTERNAL_IN)),
                           "type": "File"}
  elif (direct == "output"):
    EXTERNAL_OUT[f_name] = {"name": "ext_output_" + str(len(EXTERNAL_OUT)),
                            "type": "File",
                            "link": ""}
   

def resolve_names():

  for job in JOBS.values():
    for name, inp in job.inputs.items():
      if 'link' in inp:
        inp['value'] = inp['link']
      elif inp['value'] in EXTERNAL_IN:
        inp['value'] = EXTERNAL_IN[inp['value']]['name']
      else:
        new_name = "ext_input_" + str(len(EXTERNAL_IN))
        EXTERNAL_IN[inp['value']] = {"name": new_name,
                                     "type": inp['type']} 
        inp['value'] = new_name

    for name, out in job.outputs.items():
      if out['value'] in EXTERNAL_OUT:
        EXTERNAL_OUT[out['value']]['link'] = job.name + "/" + name
  return  


def write_output():
  data_file     = []
  workflow_file = []

  for name,exe in EXECUTABLES.items():
    with open (name + ".cwl", "w") as f:
      f.write(exe.to_cwl())

  for value, external in EXTERNAL_IN.items():
    if external['type'] == "File":
      data_file.append('"%s":{class: File, path: "%s"},' % (external['name'], value))
    else:
      data_file.append('"%s":"%s",' % (external['name'], value))

  with open("wf_data.json", "w") as f:
    f.write("{\n" + "\n".join(data_file) + "\n}")

  with open("workflow.cwl", "w") as f:
    f.write("cwlVersion: v1.0\n")
    f.write("class: Workflow\n")
    f.write("inputs:\n")

    for external in EXTERNAL_IN.values():
      f.write("  %s: %s\n" % (external['name'], external['type']))

    f.write("outputs:\n")
    for external in EXTERNAL_OUT.values():
      if external['link']:
        f.write("  %s:\n" % external['name'])
        f.write("    type: File\n")
        f.write("    outputSource: %s\n" % external['link'])

    f.write("steps:")

    for job in JOBS.values():
      f.write(job.to_cwl())



if __name__ == "__main__":
  main()
