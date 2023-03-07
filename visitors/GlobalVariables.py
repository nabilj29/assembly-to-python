import ast

class GlobalVariableExtraction(ast.NodeVisitor):
    """ 
        We extract all the left hand side of the global (top-level) assignments
    """
    
    def __init__(self) -> None:
        super().__init__()
        self.results = []

    def visit_Assign(self, node):
        if len(node.targets) != 1:
            raise ValueError("Only unary assignments are supported")
        valueExtraction = node.value.__dict__
        flag = True
        if "value" in valueExtraction.keys():
            if node.targets[0].__class__ == ast.Subscript:
                return
            for i in self.results:
                if i[0] == node.targets[0].id:
                    flag = False
                    break
            if flag:
                self.results.append([node.targets[0].id, valueExtraction["value"]])
        else:
            if node.targets[0].__class__ == ast.Subscript:
                return
            
            for i in self.results:
                if i[0] == node.targets[0].id:
                    flag = False
                    break
            if flag:
                if node.targets[0].id[-1] == "_":
                    self.results.append([node.targets[0].id, node.value.right.value*2]) 
                else:
                    self.results.append([node.targets[0].id, None]) 

    def visit_FunctionDef(self, node):
        """We do not visit function definitions, they are not global by definition"""
        pass
   