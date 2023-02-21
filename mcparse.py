#!/usr/bin/env python
# coding: utf-8

# In[26]:


# ----------------------------------------
# Created by Tanner Heatherly
# Last updated February 20th, 2023
#
# For questions/bug reports, email heathert@oregonstate.edu
#
# Documentation still needs to be written.
# ----------------------------------------

# To use, type:

#    from /path/to/file/mcparse import *

# OR if it's in your local directory:

#    from mcparse import *

# ----------------------------------------

# Features to add:
#  - Compatibility with Numpy array-type?
#  - Calculation of total T value for any standard F tally
#    even if it is not present in output.

# KNOWN ISSUES:
#  - When calling TallyCells(), the list of cells will be cut short 
#    if the tally entry is interrupted with a comment line or in-line (\$) comment.

#  - TallyValues() does not return total (T) value.

class ReadData:
    
    def __init__(self, path, front_cutoff=True):
        self.filepath = open(path, "r")
        self.lines = self.filepath.readlines()
        if front_cutoff:
            # Removes the MCNP license up to the first comment.
            # Be wary, this may not work well with other decks.
            self.lines = self.lines[37:]
            
        # Find start and end of Table 60
        # start...
        for line in self.lines:
            if "print table 60" in line:
                table_start = self.lines.index(line) + 4
        # end...
        for line in self.lines[table_start:]:
            if "total" in line:
                table_end = self.lines.index(line)
                break
                
        # Convert strings into dictionary
        self.table60 = {}
        for line in self.lines[table_start:table_end]:
            line = line.replace("\n", "")
            entry = [x for x in line.split(" ") if x]
            
            try: # Read Table 60
                if len(entry) > 0:
                    cell =       entry[1]
                    matnum =     entry[2]
                    atom_den =   entry[3]
                    mass_den =   entry[4]
                    volume =     entry[5]
                    mass_tot =   entry[6]
                    pieces =     entry[7] # What does this mean?
                    importance = entry[8]
                    
                    self.table60.update({ int(cell):[int(matnum), float(atom_den), float(mass_den),
                                                float(volume), float(mass_tot), float(pieces), float(importance)]})
            except:
                print("WARNING! Table 60 not found. Calling certain methods will not work!")
                
        ### Check for fatal errors and alert user
        for line in self.lines:
            
            if 'fatal error' in line:
                print("WARNING! Fatal error occured! Most data is unavailable!")
                break
                
            if 'run terminated because' in line and 'particles got lost' in line:
                print("WARNING! Too many particles lost! Most data is unavailable!")
                break
        
        
    #
    #
    # All methods that act on output file go below this line
    
    
    def TallyCells(self, tally_number, particle_type="n"):
        
        '''Grabs all cell numbers associated with
           a specified tally in the order they are
           labeled in the file'''
        
        delimiter = [self.lines.index(x) for x in self.lines if "       \n" in x]
        data_card_start = delimiter[1]
        data_card_end = delimiter[2]
        data_cards = self.lines[data_card_start+1:data_card_end]
        
        # Search for start of tally
        for line in data_cards:
            if f"f{tally_number}:{particle_type}" in line or f"F{tally_number}:{particle_type}" in line:
                tally_start = data_cards.index(line)
                
        # Find the end of the tally, assuming no comment lines
        for line in data_cards[tally_start+1:]:
            if not line[19] == " ": # Offset of indentation for output file
                tally_end = data_cards.index(line)
                break
        
        tally_cells_raw = data_cards[tally_start:tally_end]
        
        # Remove the tally card itself
        tally_cells_raw[0] = tally_cells_raw[0].replace(f"f{tally_number}:{particle_type}", "")
        tally_cells_raw[0] = tally_cells_raw[0].replace(f"F{tally_number}:{particle_type}", "")
        tally_cells_raw[0] = tally_cells_raw[0].replace("*", "")
        
        # Remove the label of each line, leaving the cell numbers as strings
        for i in range(len(tally_cells_raw)):
            tally_cells_raw[i] = tally_cells_raw[i][18:]
        
        # Convert raw strings into list of numbers
        tally_cells = []
        for i in range(len(tally_cells_raw)):
            middle_step = [x for x in tally_cells_raw[i].split(" ") if x]
            for j in middle_step:
                tally_cells.append(eval(j))
        
        # Finally, return a set of cells specific to this tally
        
        return tally_cells
    
    
    
    
    def TallyValues(self, tally_number, cell_list=[]):
        '''Grabs tally values corresponding 
           to tally number and cell'''
        
        # Find the start of tally cell/volume pairs
        for line in self.lines:
            if "1tally" in line and f" {tally_number} " in line:
                prelim = self.lines.index(line) + 6
                tally_values = self.lines[prelim:]
                break
        
        # Find the end of the tally values
        for line in tally_values:
            if "statistical checks" in line:
                end = tally_values.index(line)
                tally_values = tally_values[:end]
                break
        
        # Go through current list of strings and cut it off when a pure \n appears
        for line in tally_values:
            if line == '\n':
                tally_values = tally_values[:tally_values.index(line)]
                break

        # Match the first tally/volume pair with the first tally/value pair
        first_cell_word = "cell"
        first_cell_num  = [x for x in tally_values[0].split(" ") if x][1]
        for line in tally_values[1:]:
            if first_cell_num in line and first_cell_word in line:
                tally_values = tally_values[tally_values.index(line):]
        
        # Split lines into dictionary { cell1: [value1, error1] , cell2: [value2, error2] , etc...}
        # Initialize dictionary...
        cell = 0
        value = 0
        error = 0
        tally_dict = {}
        for i in range(len(tally_values)):
            if i % 3 == 0:
                cell = int([x for x in tally_values[i].split(" ") if x][1])
            if i % 3 == 1:
                value = float(eval([x for x in tally_values[i].split(" ") if x][0]))
                error = float(eval([x for x in tally_values[i].split(" ") if x][1]))
                
            tally_dict.update( {cell:[value, error]} )
        
        # Grab custom list for specific cells, if necessary
        custom_tally_dict = {}
        
        if len(cell_list) > 0:
            for cell in cell_list:
                custom_tally_dict.update( {cell:[tally_dict[cell][0], tally_dict[cell][1]] } )
                
            return custom_tally_dict
        
        else:
            return tally_dict
                                                 
            
    
    
                
    def Volumes(self, cells): 
        '''Grabs volumes from individual or list
           of cells from Table 60.'''
        
        assert type(cells) == list or type(cells) == int, AssertionError("Argument(s) must be type 'list' or 'int'")
        
        vols = {}
        
        # for single cell
        if type(cells) == int:
            if cells in self.table60:
                vols.update( {cells : self.table60[cells][3]} )
            else:
                raise Exception(f"Cell {cells} not found.")
            return vols
            
        if type(cells) == list:
            for cell in cells:
                if cell in self.table60:
                    vols.update( {cell : self.table60[cell][3]} )
                else:
                    raise Exception(f"Cell {cell} not found.")
            return vols
    
    
    
    
    def AtomDensity(self, cells):
        '''Grabs atom density from individual or list
           of cells from Table 60.'''
        
        assert type(cells) == list or type(cells) == int, AssertionError("Argument(s) must be type 'list' or 'int'")
        
        a_dens = {}
        
        # for single cell
        if type(cells) == int:
            if cells in self.table60:
                a_dens.update( {cells : self.table60[cells][1]} )
            else:
                raise Exception(f"Cell {cells} not found.")
            return a_dens
            
        if type(cells) == list:
            for cell in cells:
                if cell in self.table60:
                    a_dens.update( {cell : self.table60[cell][1]} )
                else:
                    raise Exception(f"Cell {cell} not found.")
            return a_dens
        
        
        
    def MassDensity(self, cells):
        '''Grabs mass density from individual or list
           of cells from Table 60.'''
        
        assert type(cells) == list or type(cells) == int, AssertionError("Argument(s) must be type 'list' or 'int'")
        
        m_dens = {}
        
        # for single cell
        if type(cells) == int:
            if cells in self.table60:
                m_dens.update( {cells : self.table60[cells][2]} )
            else:
                raise Exception(f"Cell {cells} not found.")
            return m_dens
            
        if type(cells) == list:
            for cell in cells:
                if cell in self.table60:
                    m_dens.update( {cell : self.table60[cell][2]} )
                else:
                    raise Exception(f"Cell {cell} not found.")
            return m_dens
        
        
    def Mass(self, cells):    
        '''Grabs total mass from individual or list
           of cells from Table 60.'''
        
        assert type(cells) == list or type(cells) == int, AssertionError("Argument(s) must be type 'list' or 'int'")
        
        mass = {}
        
        # for single cell
        if type(cells) == int:
            if cells in self.table60:
                mass.update( {cells : self.table60[cells][4]} )
            else:
                raise Exception(f"Cell {cells} not found.")
            return mass
            
        if type(cells) == list:
            for cell in cells:
                if cell in self.table60:
                    mass.update( {cell : self.table60[cell][4]} )
                else:
                    raise Exception(f"Cell {cell} not found.")
            return mass
        
    
    
    def Imp(self, cells):    
        '''Grabs cell importance from individual or list
           of cells from Table 60.'''
        
        assert type(cells) == list or type(cells) == int, AssertionError("Argument(s) must be type 'list' or 'int'")
        
        imp = {}
        
        # for single cell
        if type(cells) == int:
            if cells in self.table60:
                imp.update( {cells : self.table60[cells][6]} )
            else:
                raise Exception(f"Cell {cells} not found.")
            return imp
            
        if type(cells) == list:
            for cell in cells:
                if cell in self.table60:
                    imp.update( {cell : self.table60[cell][6]} )
                else:
                    raise Exception(f"Cell {cell} not found.")
            return imp
    
    
    def Matcard(self, cells):    
        '''Grabs material card from individual or list
           of cells from Table 60.'''
        
        assert type(cells) == list or type(cells) == int, AssertionError("Argument(s) must be type 'list' or 'int'")
        
        mcard = {}
        
        # for single cell
        if type(cells) == int:
            if cells in self.table60:
                mcard.update( {cells : self.table60[cells][0]} )
            else:
                raise Exception(f"Cell {cells} not found.")
            return mcard
            
        if type(cells) == list:
            for cell in cells:
                if cell in self.table60:
                    mcard.update( {cell : self.table60[cell][0]} )
                else:
                    raise Exception(f"Cell {cell} not found.")
            return mcard
    
    
        
    def NPS(self):
        '''Returns number of simulated particles.
           Notifies if file did not finish correctly.'''
        
        for line in self.lines[-50:]:
            if "run terminated when" in line:
                entry = [x for x in line.split(" ") if x]
                nps = int(entry[3])
                break
            elif "probid" in line:
                raise Exception("NPS not found. Did your output finish running?")
        return nps
    
    
    
    
    
    def Keff(self):
        return
    
    
    
    
    # All methods that act on output file go above this line
    #
    #
        
    # Final function - close output
    def close(self):
        if self.filepath:
            self.filepath.close()
            self.filepath = None


# In[48]:


output = r"C:\Users\tanhe\Desktop\NSE 474\outp.i"
output2 = r"C:\Users\tanhe\Downloads\Project1Part1.3out"

### Initialize file ###
results = ReadData(output)

### Test certain methods ###
TallyCells = results.TallyCells(4)
#print(TallyCells)

#print(results.TallyValues(tally_number=4, cell_list = [101,293]))

print(results.Volumes([101,2, 10000]))
# results.AtomDensity(TallyCells)
# results.MassDensity(TallyCells)
# results.Mass(TallyCells)
# results.Imp(TallyCells)
# results.Matcard(TallyCells)
results.NPS()


# In[ ]:




