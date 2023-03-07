
class StaticMemoryAllocation():

    def __init__(self, global_vars: dict()) -> None:
        self.global_vars = global_vars
        self.symbolTable()

    def generate(self):
        print("\n; GLOBAL SYMBOL TABLE")
        print(f'; Previous Variable\tNew Variable')
        for n in self.global_vars:
            print(f'; {str(n[0]+": "):<9}\t\t'+str(n[2]))

        print('\n; Allocating Global (static) memory')
        for n in self.global_vars:
            if (n[1] == None):
                print(f'{str(n[2]+":"):<9}\t.BLOCK 2') # reserving memory
                n.append("BLOCK")
                n.append(0)
                n.append(0)
            else:
                if n[0][0] == "_" and n[0][1:].isupper():
                    print(f'{str(n[2]+":"):<9}\t.EQUATE '+str(n[1]))
                    n.append("EQUATE")
                    n.append(0)
                    n.append(0)
                elif n[0][-1] == "_":
                    print(f'{str(n[2]+":"):<9}\t.BLOCK '+str(n[1]))
                    n.append("BLOCK")
                    n.append(0)
                    n.append(0)
                else:
                    print(f'{str(n[2]+":"):<9}\t.WORD '+str(n[1]))
                    n.append("WORD")
                    n.append(0)
                    n.append(0)

    def symbolTable(self):
        random = "A" 
        for n in self.global_vars:
            n.append(random)
            temp = list(random)
            if(ord(random[-1]) == 90):
                random+="A"
            else:
                temp[-1] = chr(ord(temp[-1])+1)
            random = ''.join(temp)


                

