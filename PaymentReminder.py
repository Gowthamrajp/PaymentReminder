import pandas as pd
import os;
import pywhatkit

global count 
count =0
global unpaid 
unpaid =0
global paid
paid=0
customerData = pd.read_csv (os.getcwd()+"\CustomerData.csv")  

def sender(number,name,amount,cycle,isPaid):
    global count
    global unpaid
    global paid
    if(isPaid!="paid"):        
        count=count+1
        unpaid+=amount
        pywhatkit.sendwhatmsg_instantly("+"+str(number),"Dear Customer,\nPlease pay Cable TV amount for "+cycle+" month Rs"+str(amount)+"via Gpay/Paytm/phonepay/WhatsApp\n\n9444047656 ( Pandian )  Rs "+str(amount)+" \nPlease Send screen shot of payment receipt if possible\n\nIgnore if Paid \n\nThank you for your kind Co-operation.Have a Nice day"+"\U0001F64F",15,True,3)
        print(str(x+1)+". Reminder sent to "+name )
    else:
        paid+=amount
    

for x in range(0,len(customerData["Number"])):
        sender(customerData["Number"][x], customerData["Name"][x], customerData["Amount"][x], customerData["Cycle"][x] , customerData["Status"][x])

pywhatkit.sendwhatmsg_to_group_instantly("Lm8d0hUAh6AFez1pCeg9hm","TOTAL NUMBER OF ONLINE CUSTOMERS: "+str(len(customerData["Number"]))+"\nPAYMENT REQUEST SENT TO: "+str(count)+" customers"+"\nPAYMENT REQUEST IGNORED FOR: "+str(len
(customerData["Number"])-count)+" paid customers"+"\nTOTAL AMOUNT COLLECTED VIA ONLINE: Rs."+str(paid)+"\nTOTAL AMOUNT PENDING: Rs."+str(unpaid))


print("TOTAL NUMBER OF ONLINE CUSTOMERS: "+str(len(customerData["Number"])))
print("PAYMENT REQUEST SENT TO: "+str(count)+" customers")
print("PAYMENT REQUEST IGNORED FOR: "+str(len
(customerData["Number"])-count)+" paid customers")
print("TOTAL AMOUNT COLLECTED VIA ONLINE: Rs."+str(paid))
print("TOTAL AMOUNT PENDING: Rs."+str(unpaid))
        