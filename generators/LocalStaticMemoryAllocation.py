
class LocalStaticMemoryAllocation():

    def __init__(self, symbolTable) -> None:
        self.symbolTable = symbolTable

    def generate(self, local_vars):
        self.local_vars = self.symbolTable.generate(local_vars)
        #count the number of times local appears in self.local_vars using count()
        temp = []
        for i in self.local_vars:
            if i[2] == "Local" or i[2]=="ReturnValue" or i[2]== "Args":
                temp.append(i)
        
        if len(temp) > 0:
            print("\n; LOCAL SYMBOL TABLE")
            print(f'; Previous Variable\tNew Variable')
            for n in self.local_vars:
                print(f'; {str(n[0]+": "):<9}\t\t'+str(n[3]))
            print('\n; Allocating Local memory')

            for i in self.local_vars:
                print(f'{str(i[3]+":"):<9}\t.EQUATE {i[1]}')


        print("\n")   

        return self.local_vars            

