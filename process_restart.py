''' Description:
Preliminary code to handle binary restart files generated and read by Serpent
Tested with a simple pbed geometry with a unique parent material divided over the pebbles
'''

#%% Modules
import struct
import sys

if sys.version_info[0] < 3:
    from StringIO import StringIO
else:
    from io import StringIO


#%% Classes and functions
class Material:
    def read(self, file, prefix):
        ''' Read block in binary file for a new material'''
        self.file_name = file.name
        s = file.read(8)
        if not s: # Test if we reached the end of the file
            return False 
        
        # Read name
        n = struct.unpack("q", s)[0]  # len of material name
        self.name = struct.unpack("{}s".format(n), file.read(n))[
            0].decode('UTF-8') # Material name
        if self.name == prefix: # Test if material is parent or divided
            self.parent = True
        else:
            self.parent = False
            self.id = int(self.name.split(prefix+'z')[1]) # Assign id of the divided material

        # Read material info
        self.bu_global = struct.unpack("d", file.read(8))[0] # BU point 
        self.bu_days = struct.unpack("d", file.read(8))[0] # BU point in days 
        self.nnuc = struct.unpack("q", file.read(8))[0] # Number of nuclides contained in material
        self.adens = struct.unpack("d", file.read(8))[0] # Material atomic density
        self.mdens = struct.unpack("d", file.read(8))[0] # Material mass density
        self.bu = struct.unpack("d", file.read(8))[0] # Material (local) burnup
        
        # Read nuclides info
        self.nuclides = dict()
        for i in range(self.nnuc):
            ZAI, adens = struct.unpack("qd", file.read(16))
            self.nuclides[str(ZAI)] = dict()
            self.nuclides[str(ZAI)]['adens'] = adens # Atomic density
        return True

    def to_binary(self):
        ''' Write block in binary file for a this material'''
        content = b''
        content += struct.pack('q', len(self.name)) 
        content += struct.pack('{}s'.format(len(self.name)), str.encode(self.name))
        content += struct.pack('d', self.bu_global)
        content += struct.pack('d', self.bu_days)
        content += struct.pack('q', self.nnuc)
        content += struct.pack('d', self.adens)
        content += struct.pack('d', self.mdens)
        content += struct.pack('d', self.bu)
        for i in self.nuclides:
            content += struct.pack('q', int(i))
            content += struct.pack('d', self.nuclides[i]['adens'])
        return content

    def __repr__(self):
        ''' Prints material info in a human readable way '''
        s  = 'Material information'
        s += ' - Name: {}\n'.format(self.name)
        s += ' - File: {}\n'.format(self.file_name)
        s += ' - BU point: {:.3f} MWd/kg ({:.3f} days)\n'.format(self.bu_global, self.bu_days)
        s += ' - Density: {:.3E} at/b.cm ({:.3E} g/cm^3)\n'.format(self.adens, self.mdens)
        s += ' - Local BU: {:.3f} MWd/kg\n'.format(self.bu)
        s += ' - Nuclides:\n'
        for i in self.nuclides:
            s += '    {:6}: {:.3E} at/b.cm\n'.format(i, self.nuclides[i]['adens'])
        return s

def read_binary(path_in, prefix):
    ''' Read whole binary file, creating materials on the way '''

    print('Reading material information in {}'.format(path_in))

    # Initialize
    burnups = [] # list of burnup points in the file (p/c has multiple bu points)
    snapshots = dict() 
    current_step = -1

    # Read binary file
    with open(path_in, mode='rb') as file:
        while True:
            # Create material and fill it by reading one material block
            mat = Material() 
            read_ok = mat.read(file, prefix)

            # Stop if reached end of file
            if not read_ok:
                break

            # If new burnup, initialize a new snapshot and add the material
            if len(burnups) == 0 or mat.bu_global != burnups[-1]:
                current_step += 1
                snapshots[current_step] = dict()
                snapshots[current_step]['materials'] = dict()
                burnups.append(mat.bu_global)
            # If existing burnup, add the material to the current snapshot
            else:
                snapshots[current_step]['materials'][mat.name] = mat

    print('\tDone reading')
    return snapshots

def write_binary(path_out, snapshots):
    ''' Create binary file from snapshots containing materials '''
    
    print('Write material information for in {}'.format(path_out))

    # Loop over snapshots
    contents = []
    for i_step in snapshots:
        materials = snapshots[i_step]['materials']
        
        # Loop over materials 
        for i in materials:
            contents.append(materials[i].to_binary()) # Create binary material block

    # Write blocks to binary file
    with open(path_out, 'wb') as f:
        f.write(b''.join(contents))

    print('\tDone writing')


#%% Test
if __name__ == '__main__':
    #%% Input data
    folder = './test/Serpent_calculations/step1/' # Folder containing restart file
    file_in = 'materials1.wrk' # File to read
    file_out = 'test.wrk' # File to write after modification
    prefix = 'fuel20U' # Name of the divided parent material to extract 

    # Read original file
    snapshots = read_binary(folder+file_in, prefix)
    print(snapshots[0]['materials']['fuel20Uz1']) # Print initial material information
    
    # Modify one material for test purposes and write to new file
    snapshots[0]['materials']['fuel20Uz1'].adens = 1e3 # Huge value for tests
    write_binary(folder+file_out, snapshots) # Write

    # Read new modified file
    snapshots2 = read_binary(folder+file_out, prefix)
    print(snapshots2[0]['materials']['fuel20Uz1']) # Print new material information
