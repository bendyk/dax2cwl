import re

class Executable:
 
  def __init__(self, name, xml_body):
    self.inputs  = []
    self.outputs = []
    self.name    = name

    self.parse_files(xml_body)
    self.parse_arguments(xml_body)


  def parse_arguments(self, xml_body):
    counter   = 0
    args      = []
    arguments = xml_body[xml_body.index("<argument>")+1 : xml_body.index("</argument>")]
       
    for argument in arguments:
      if argument:
        counter += 1
        if "<filename" in argument:
          prefix = argument.split("<filename")[0]
          f_name = argument.split('"')[1]

          for inp in self.inputs:
            if f_name in inp["value"]:
              inp["binding"] = counter
              if prefix: inp["prefix"] = prefix

        else:
          args.append({"name"    : "in_arg_" + str(len(args)),
                       "value"   : argument.strip(),
                       "type"    : "string",
                       "binding" : counter}) 

    self.inputs.extend(args)
        

  def parse_files(self, xml_body):

    regex  = re.compile('.*file="([^"]*)".*link="([^"]*)".*/>')

    for line in xml_body:

      if line.strip().startswith("<uses") and not ("type" in line):

        match  = regex.match(line.strip())
        f_name = match.group(1)
        direct = match.group(2)
 
        if direct in "input":
          self.inputs.append({ "name"  : "in_file_" + str(len(self.inputs)),
                               "value" : f_name,
                               "type"  : "File"})

        elif direct in "output":
          self.inputs.append({ "name"  : "name_file_" + str(len(self.outputs)),
                               "value" : f_name,
                               "type"  : "string"})

          self.outputs.append({"name"  : "out_file_" + str(len(self.outputs)),
                               "value" : "name_file_" + str(len(self.outputs)),
                               "type"  : "File"})


  def get_unbound_inputs(self):
    unbound = []
    for inp in self.inputs:
      if not("binding" in inp) and (inp["type"] == "File"):
        unbound.append(inp["name"])
    return unbound

  def get_unbound_outputs(self):
    unbound = []
    for out in self.outputs:
      bound = False
      for inp in self.inputs:
        if (inp["name"] == out["value"]) and ("binding" in inp):
          bound = True
     
      if not bound: unbound.append(out['name'])
  
    return unbound


  def name_of_binding(self, number):
    ret = ""
    for inp in self.inputs:
      if "binding" in inp and inp["binding"] == number:
        ret = inp["name"]
        break

    return ret


  def to_cwl(self):
    cwl_file = """cwlVersion: v1.0
class: CommandLineTool
baseCommand: %(cmd)s
inputs:
%(inputs)s
outputs:
%(outputs)s"""

    inputs  = []
    outputs = []

    for inp in self.inputs:
      txt = []
      txt.append("  %s:" % inp['name'])
      txt.append("    type: %s" % inp['type']) 
      if "binding" in inp:
        txt.append("    inputBinding:")
        txt.append("      position: %d" % inp['binding'])

      inputs.append("\n".join(txt))

    for out in self.outputs:
      txt = []
      txt.append("  %s" % out['name'])
      txt.append("    type: %s" % out['type'])
      txt.append("    outputBinding:")
      txt.append("      glob: $(inputs.%s)" % out['value'])

      outputs.append("\n".join(txt))

    return cwl_file % {"cmd" : self.name, "inputs" : "\n".join(inputs) , "outputs" : "\n".join(outputs)} 
