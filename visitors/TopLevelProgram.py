import ast
from generators.LocalStaticMemoryAllocation import LocalStaticMemoryAllocation
from generators.SymbolTable import SymbolTable
from visitors.FunctionLevelProgram import FunctionLevelProgram
from visitors.LocalVariable import LocalVariableExtraction
from generators.LocalEntryPoint import LocalEntryPoint


LabeledInstruction = tuple[str, str]

class TopLevelProgram(ast.NodeVisitor):
    """We supports assignments and input/print calls"""

    def __init__(self, entry_point, temp_var) -> None:
        super().__init__()
        self.__instructions = list()
        self.__record_instruction('NOP1', label=entry_point)
        self.__should_save = True
        self.temp_var = temp_var
        self.__current_variable = None
        self.__elem_id = 0
        self.defFunction = {}
        self.symbolTable = SymbolTable()
        self.unique = 1

    def finalize(self):
        self.__instructions.append((None, '.END'))
        return self.__instructions

    ####
    # Handling Assignments (variable = ...)
    ####

    def visit_Assign(self, node):
        # to see if the assign is it 

        flag = False
        for i in self.temp_var:
            if node.targets[0].__class__ == ast.Subscript:
                self.__current_variable = i[2]
                
            elif i[0] == node.targets[0].id:
                self.__current_variable = i[2]
                break
        
        if node.value.__class__ == ast.BinOp and node.value.op.__class__ == ast.Mult:
            return

        
        # visiting the left part, now knowing where to store the result
        self.visit(node.value)

        self.Should_Save(self.__current_variable)
        
        if node.value.__class__ == ast.Constant:
            self.Constant_Decision(node)

        elif "func" in node.value.__dict__.keys() and node.value.func.id in self.defFunction.keys():
            self.__record_instruction(f'LDWA 0,s')
            flag = True

        if self.__should_save:
            self.__record_instruction(f'STWA {self.__current_variable},d')
        else:
            self.__should_save = True

        if flag:
            self.__record_instruction(f'ADDSP 2,i')
        
        if node.targets[0].__class__ == ast.Subscript:
            self.visit(node.targets[0])
            return
        self.__current_variable = None


    def visit_Subscript(self, node):

        for i in self.temp_var:
            if i[0] == node.value.id:
                temp = i[2]
            
            elif i[0] == node.slice.id:
                index = i[2]

        self.__record_instruction(f'LDWX {index},d')
        self.__record_instruction(f'ASLX')
        self.__record_instruction(f'STWA {temp},x')

    def Should_Save(self,currentVar):
        for i in self.temp_var:
            if (i[2] == currentVar and i[3] == "EQUATE") or (i[2] == currentVar and i[4] == 0 and i[3] == "WORD"):
                self.__should_save = False
                i[4] += 1
                break

    def Constant_Decision(self, node):
        flag = True
        for i in self.temp_var:
            if i[2] == self.__current_variable and i[5] == 0:
                i[5] += 1
                flag = False
                break
        if flag:
            self.__record_instruction(f'LDWA {node.value.value},i')

    def visit_Name(self, node):
        for i in self.temp_var:
            if i[0] == node.id:
                temp = i[2]
                break
        self.__record_instruction(f'LDWA {temp},d')

    def visit_BinOp(self, node):
        self.__access_memory(node.left, 'LDWA')
        if isinstance(node.op, ast.Add):
            self.__access_memory(node.right, 'ADDA')
        elif isinstance(node.op, ast.Sub):
            self.__access_memory(node.right, 'SUBA')
        else:
            raise ValueError(f'Unsupported binary operator: {node.op}')

    def visit_Call(self, node):
        match node.func.id:
            
            case 'int':
                # Let's visit whatever is casted into an int
                self.visit(node.args[0])
            
            case 'input':
                # We are only supporting integers for now
                self.__record_instruction(f'DECI {self.__current_variable},d')
                self.__should_save = False  # DECI already save the value in memory
            
            case 'print':
                if "args" in node.__dict__.keys() and node.args[0].__class__ == ast.Subscript:
                    for i in self.temp_var:
                        if i[0] == node.args[0].value.id:
                            temp = i[2]
                        
                        elif i[0] == node.args[0].slice.id:
                            index = i[2]
                    self.__record_instruction(f'LDWX {index},d')
                    self.__record_instruction(f'ASLX')
                    self.__record_instruction(f'DECO {temp},x')
                    return
                # We are only supporting integers for now
                for i in self.temp_var:
                    if i[0] == node.args[0].id:
                        temp = i[2]
                        break
                self.__record_instruction(f'DECO {temp},d')
            
            case 'exit':
                self.__record_instruction(f'STOP')
            case _:               
                args = [arg.id for arg in node.args]

                self.funcExtraction(node, args)
                
                for i in self.temp_var:
                    if i[0] in args:
                        args[args.index(i[0])] = i[2]

                for i in range(len(args)):
                    self.__record_instruction(f'LDWA {args[i]},d')
                    self.__record_instruction(f'STWA {i*2},s')
                self.__record_instruction(f'CALL {node.func.id}')
                
                if args:
                    self.__record_instruction(f'ADDSP {len(args)*2}, i')
                

    #visit the function and get the instructions using stack 
    def visit_FunctionDef(self, node):
        if node.name not in self.defFunction:
            self.defFunction[node.name] = node

        args = [arg.arg for arg in node.args.args]

        mod = ast.Module()
        mod.body = node.body
        
        extractor = LocalVariableExtraction()
        extractor.visit(mod)

        for i in range(len(extractor.results)):
            extractor.results[i][1] = i*2
            extractor.results[i].append("Local")

        for i in extractor.results:
            for j in args:
                if i[0] == j:
                    extractor.results.remove(i)
                    break
        for i in range(len(args)):
                extractor.results.append([args[i],(len(extractor.results)+1)*2,'Args'])
        
        for i in node.body:
            if i.__class__ == ast.Return:
                extractor.results.append(["retVal",(1+len(extractor.results))*2,"ReturnValue"])
                break
        
        memory_alloc = LocalStaticMemoryAllocation(self.symbolTable)
        memory_alloc.generate(extractor.results)
        top_level = FunctionLevelProgram(node.name, memory_alloc.local_vars, self.temp_var, self.defFunction,self.unique)
        top_level.visit(mod)
        ep = LocalEntryPoint(top_level.finalize())
        ep.generate()
        self.unique +=1

    def funcExtraction(self,node,args):
        for i in self.defFunction:
            if node.func.id == i:
                nodeFunc = self.defFunction[i]
        returnFlag = False
        for i in nodeFunc.body:
            if i.__class__ == ast.Return:
                returnFlag = True
                break
        if len(args) != 0 or returnFlag:
            self.__record_instruction(f'SUBSP {(len(args)+returnFlag)*2},i')
    
    ####
    # Handling While loops (only variable OP variable)
    ####

    def visit_While(self, node):
        #print(node.__dict__)
        
        for i in node.__dict__['body']:
            
            if i.__class__ == ast.Assign and i.value.__class__ == ast.Constant:
                if i.targets[0].__class__ == ast.Subscript:
                    continue
                for n in self.temp_var:
                    if n[0] == i.targets[0].id:
                        n[4] +=1
                        n[5] +=1
        loop_id = self.__identify()
        inverted = {
            ast.Lt:  'BRGE',  # '<'  in the code means we branch if '>='
            ast.LtE: 'BRGT',  # '<=' in the code means we branch if '>'
            ast.Gt:  'BRLE',  # '>'  in the code means we branch if '<='
            ast.GtE: 'BRLT',  # '>=' in the code means we branch if '<'
            ast.NotEq: 'BREQ',  # '!=' in the code means we branch if '=='
            ast.Eq: 'BRNE'  # '==' in the code means we branch if '!='
        }
        # left part can only be a variable
        self.__access_memory(node.test.left, 'LDWA', label=f'test_{loop_id}')
        # right part can only be a variable
        self.__access_memory(node.test.comparators[0], 'CPWA')
        # Branching is condition is not true (thus, inverted)
        self.__record_instruction(
            f'{inverted[type(node.test.ops[0])]} end_l_{loop_id}')
        # Visiting the body of the loop
        for contents in node.body:
            self.visit(contents)
        self.__record_instruction(f'BR test_{loop_id}')
        # Sentinel marker for the end of the loop
        self.__record_instruction(f'NOP1', label=f'end_l_{loop_id}')

    ####
    # Not handling function calls
    ####
    
    #function to handle If, Elif and Else statements
    def visit_If(self, node):
        if node.orelse:
            self.__if_else(node)
        else:
            self.__if(node)
        
    def __if(self, node):
        if_id = self.__identify()
        inverted = {
            ast.Lt:  'BRGE',  # '<'  in the code means we branch if '>='
            ast.LtE: 'BRGT',  # '<=' in the code means we branch if '>'
            ast.Gt:  'BRLE',  # '>'  in the code means we branch if '<='
            ast.GtE: 'BRLT',  # '>=' in the code means we branch if '<'
            ast.NotEq: 'BREQ',  # '!=' in the code means we branch if '=='
            ast.Eq: 'BRNE'  # '==' in the code means we branch if '!='
        }
        # left part can only be a variable
        self.__access_memory(node.test.left, 'LDWA', label=f'test_{if_id}')
        # right part can only be a variable
        self.__access_memory(node.test.comparators[0], 'CPWA')
        # Branching is condition is not true
        self.__record_instruction(
            f'{inverted[type(node.test.ops[0])]} end_i_{if_id}')
        # Visiting the body of the loop
        for contents in node.body:
            self.visit(contents)
        # end of the loop
        self.__record_instruction(f'NOP1', label=f'end_i_{if_id}')
    
    def __if_else(self, node):
        if_id = self.__identify()
        inverted = {
            ast.Lt:  'BRGE',  # '<'  in the code means we branch if '>='
            ast.LtE: 'BRGT',  # '<=' in the code means we branch if '>'
            ast.Gt:  'BRLE',  # '>'  in the code means we branch if '<='
            ast.GtE: 'BRLT',  # '>=' in the code means we branch if '<'
            ast.NotEq: 'BREQ',  # '!=' in the code means we branch if '=='
            ast.Eq: 'BRNE'  # '==' in the code means we branch if '!='
        }
        # left part can only be a variable
        self.__access_memory(node.test.left, 'LDWA', label=f'test_{if_id}')
        # right part can only be a variable
        self.__access_memory(node.test.comparators[0], 'CPWA')
        # Branching is condition is not true
        self.__record_instruction(
            f'{inverted[type(node.test.ops[0])]} else_{if_id}')
        # Visiting the body of the loop
        for contents in node.body:
            self.visit(contents)
        self.__record_instruction(f'BR end_i_{if_id}')
        #end of the loop
        self.__record_instruction(f'NOP1', label=f'else_{if_id}')
        for contents in node.orelse:
            self.visit(contents)
        self.__record_instruction(f'NOP1', label=f'end_i_{if_id}')
    


    ####
    # Helper functions to
    ####

    def __record_instruction(self, instruction, label=None):
        self.__instructions.append((label, instruction))

    def __access_memory(self, node, instruction, label=None):
        #print(instruction,node.id if node.id else node.value, label)
        flag = False
        for i in self.temp_var:
            if node.__class__ != ast.Constant and i[3] == "EQUATE" and i[0] == node.id:
                temp = i
                flag = True
                break

        if isinstance(node, ast.Constant) or flag:
            if flag:
                self.__record_instruction(f'{instruction} {temp[2]},i', label)
            else:
                self.__record_instruction(
                    f'{instruction} {node.value},i', label)
        else:
            if node.__class__ == ast.List:
                print("Next")
            for i in self.temp_var:
                if i[0] == node.id:
                    temp = i[2]
                    break
            self.__record_instruction(f'{instruction} {temp},d', label)

    def __identify(self):
        result = self.__elem_id
        self.__elem_id = self.__elem_id + 1
        return result

#modify the code above to work for functions and local variables rather than just global variables in PEP9