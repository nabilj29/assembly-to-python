import ast
from generators.LocalEntryPoint import LocalEntryPoint
from generators.LocalStaticMemoryAllocation import LocalStaticMemoryAllocation

from visitors.LocalVariable import LocalVariableExtraction

LabeledInstruction = tuple[str, str]


class FunctionLevelProgram(ast.NodeVisitor):
    """We supports assignments and input/print calls"""

    def __init__(self, entry_point, temp_var, global_var, defFunc, unique) -> None:
        super().__init__()
        self.__instructions = list()
        self.__should_save = True
        self.temp_var = temp_var
        self.__current_variable = None
        self.__elem_id = 0
        self.global_var = global_var
        self.defFunction =defFunc
        self.unique = unique
        self.count = 0
        self.args = 0
        for i in self.temp_var:
            if i[2] == 'Local':
                self.count += 1
        if self.count > 0:
            self.__record_instruction(f'SUBSP {self.count*2},i',label = entry_point)


    def finalize(self):
        if self.count > 0:
            self.__record_instruction(f'ADDSP {self.count*2},i')
        self.__instructions.append((None, 'RET'))
        return self.__instructions

    ####
    # Handling Assignments (variable = ...)
    ####

    def visit_Assign(self, node):
        flag = False
        for i in self.temp_var:
            if i[0] == node.targets[0].id:
                self.__current_variable = i
                break
                
        # visiting the left part, now knowing where to store the result
        self.visit(node.value)
        # if "func" in node.value.__dict__.keys():
        #     print(node.__dict__)
        #     print(node.value.func.__dict__)
        if "func" in node.value.__dict__.keys() and node.value.func.id in self.defFunction.keys():
            self.__record_instruction(f'LDWA 0,s')
            flag = True
        if self.__should_save:
            if flag:
                self.__record_instruction(f'STWA {self.__current_variable[1]+2},s')
            else:
                self.__record_instruction(f'STWA {self.__current_variable[3]},s')
        
        else:
            self.__should_save = True

        if flag:
            self.__record_instruction(f'ADDSP 2,i')

        self.__current_variable = None

    def visit_Constant(self, node):
        self.__record_instruction(f'LDWA {node.value},i')
    
    def visit_Name(self, node):
        for i in self.temp_var:
            if i[0] == node.id:
                temp = i[3]
                break
        self.__record_instruction(f'LDWA {temp},s')

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
                
                self.__record_instruction(f'DECI {self.__current_variable[3]},s')
                self.__should_save = False # DECI already save the value in memory
            case 'print':
                for i in self.temp_var:
                    if i[0] == node.args[0].id:
                        temp = i[3]
                        break
                # We are only supporting integers for now
                self.__record_instruction(f'DECO {temp},s')
            case _:
                args = [arg.id for arg in node.args]
                offset = self.funcExtraction(node, args)
                
                #print(self.temp_var, self.global_var, args)
                for i in self.temp_var:
                    if i[0] in args:
                        args[args.index(i[0])] = i[3]

                for i in range(len(args)):
                    for j in self.temp_var:
                        if args[i] == j[3]:
                            self.__record_instruction(f'LDWA {offset+j[1]},s')
                            break
                    self.__record_instruction(f'STWA {i*2},s')
                self.__record_instruction(f'CALL {node.func.id}')
                
                if args:
                    self.__record_instruction(f'ADDSP {len(args)*2},i')
                    self.args = len(args)*2

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

        return (len(args)+returnFlag)*2

    def visit_Return(self, node):
        #print(node.value.value)
        for i in self.temp_var:
            if i[2] == "ReturnValue":
                temp = i[3]
        if node.value.__class__ == ast.Constant:
            
            self.__record_instruction(f'LDWA {node.value.value},i')
            self.__record_instruction(f'STWA {temp},s')
            self.__record_instruction(f'ADDSP {self.count*2},i')
            self.__record_instruction(f'RET')
        else:
            for i in self.temp_var:          
                if i[0] == node.value.id:
                    temp2 = i[3]
                    break

            self.__record_instruction(f'LDWA {temp2},s')
            self.__record_instruction(f'STWA {temp},s')
        

    ####
    ## Handling While loops (only variable OP variable)
    ####

    def visit_While(self, node):
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
        self.__access_memory(node.test.left, 'LDWA', label=f'test_{loop_id+self.unique}')
        # right part can only be a variable
        self.__access_memory(node.test.comparators[0], 'CPWA')
        # Branching is condition is not true (thus, inverted)
        self.__record_instruction(
            f'{inverted[type(node.test.ops[0])]} end_l_{loop_id+self.unique}')
        # Visiting the body of the loop
        for contents in node.body:
            self.visit(contents)
        self.__record_instruction(f'BR test_{loop_id+self.unique}')
        # Sentinel marker for the end of the loop
        self.__record_instruction(f'NOP1', label=f'end_l_{loop_id+self.unique}')

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
        self.__access_memory(node.test.left, 'LDWA', label=f'test_{if_id+self.unique}')
        # right part can only be a variable
        self.__access_memory(node.test.comparators[0], 'CPWA')
        # Branching is condition is not true
        self.__record_instruction(
            f'{inverted[type(node.test.ops[0])]} end_i_{if_id+self.unique}')
        # Visiting the body of the loop
        for contents in node.body:
            self.visit(contents)
        # end of the loop
        self.__record_instruction(f'NOP1', label=f'end_i_{if_id+self.unique}')
    
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
        self.__access_memory(node.test.left, 'LDWA', label=f'test_{if_id+self.unique}')
        # right part can only be a variable
        self.__access_memory(node.test.comparators[0], 'CPWA')
        # Branching is condition is not true
        self.__record_instruction(
            f'{inverted[type(node.test.ops[0])]} else_{if_id+self.unique}')
        # Visiting the body of the loop
        for contents in node.body:
            self.visit(contents)
        self.__record_instruction(f'BR end_i_{if_id+self.unique}')
        #end of the loop
        self.__record_instruction(f'NOP1', label=f'else_{if_id+self.unique}')
        for contents in node.orelse:
            self.visit(contents)
        self.__record_instruction(f'NOP1', label=f'end_i_{if_id+self.unique}')

    ####
    ## Helper functions to 
    ####

    def __record_instruction(self, instruction, label = None):
        self.__instructions.append((label, instruction))

    def __access_memory(self, node, instruction, label = None):
        flag = False
        for i in self.global_var:
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
            flag = False
            for i in self.temp_var:
                if i[0] == node.id:
                    temp = i
                    flag = True
                    break
                else:
                    temp = node.id
            if flag:
                self.__record_instruction(f'{instruction} {temp[3]},s', label)
            else:
                for i in self.global_var:
                    if i[0] == node.id:
                        temp = i[2]
                        flag = True
                        break

                self.__record_instruction(f'{instruction} {temp},d', label)
    def __identify(self):
        result = self.__elem_id
        self.__elem_id = self.__elem_id + 1
        return result
