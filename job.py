import re

class Job:
  def __init__(self, name, executable, xml):
    self.name         = name
    self.executable   = executable
    self.inputs       = {}
    self.outputs      = {}
    self.arguments    = {}

    self.parse_arguments(xml)
    self.parse_files(xml)

  def parse_arguments(self, xml_body):
    counter = 0
    arguments = xml_body[xml_body.index("<argument>")+1 : xml_body.index("</argument>")]

    for argument in arguments:
      if argument.strip():
        counter += 1

        if "<filename" in argument:
          f_name = argument.split('"')[1]
          self.arguments[f_name] = self.executable.name_of_binding(counter)
        else:
          self.inputs[self.executable.name_of_binding(counter)] = {"value": argument.strip(), "type": "string"}


  def parse_files(self, xml_body):

    regex           = re.compile('.*file="([^"]*)".*link="([^"]*)".*/>')
    unbound_inputs  = self.executable.get_unbound_inputs()
    unbound_outputs = self.executable.get_unbound_outputs()


    for line in xml_body:

      if line.strip().startswith("<uses") and not ("type" in line):

        match  = regex.match(line.strip())
        f_name = match.group(1)
        direct = match.group(2)
                
        if direct in "input":
          if f_name in self.arguments:
            self.inputs[self.arguments[f_name]] = {"value" : f_name, "type" : "File"}
          else:
            self.inputs[unbound_inputs.pop(0)] = {"value" : f_name, "type" : "File"}

        elif direct == "output":
          if f_name in self.arguments:
            self.inputs[self.arguments[f_name]] = {"value" : f_name, "type" : "string"}
            self.outputs[self.arguments[f_name].replace("name", "out")] = {"value" : f_name, "type" : "File"}
          else:
            name = unbound_outputs.pop(0)
            self.inputs[name.replace("out", "name")] = {"value": f_name, "type": "string"}
            self.outputs[name] = {"value" : f_name, "type" : "File"}

  
  def to_cwl(self):
    cwl_step = """
  %(name)s:
    run: %(cmd)s.cwl
    in:
%(inputs)s
    out: [%(outputs)s]"""

    inputs  = []
    outputs = []

    for name, inp in self.inputs.items():
      txt = []
      if inp['type'] == "File":
        txt.append("      %s:" % name)
        txt.append("        source: %s" % inp["value"])
      else:
        txt.append("      %s: %s" % (name, inp["value"]))
      inputs.append("\n".join(txt))

    for name in self.outputs:
      outputs.append(name)

    return cwl_step % {"name": self.name, "cmd": self.executable.name, 
                       "inputs": "\n".join(inputs), "outputs": ", ".join(outputs)}
