import hou
"""
# Execute the opextern command
command = "opextern -gRrm /" 
# command = "opextern -rR /" # Prints all externals references
result = hou.hscript(command)

# result is a tuple where the first element is the command's stdout
output = result[0]
external_files = output.strip().split('\n')
"""

output = hou.fileReferences()

# Print or process the output
print(output)

# print(str(len(output))+" external files.")