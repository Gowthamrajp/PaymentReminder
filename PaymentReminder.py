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
        pywhatkit.sendwhatmsg_instantly("+"+str(number),"Dear Customer, Please pay Cable TV amount for "+cycle+" month Rs"+str(amount)+"via Gpay/Paytm/phonepay/WhatsApp\n\n  9444047656 ( Pandian )  Rs "+str(amount)+" \n  Please Send screen shot of payment receipt if possible\n   ignore if Paid \n Thank you Have a Nice day")
        print(str(x+1)+". Reminder sent to "+name )
    else:
        paid+=amount
    

for x in range(0,len(customerData["Number"])):
        sender(customerData["Number"][x], customerData["Name"][x], customerData["Amount"][x], customerData["Cycle"][x] , customerData["Status"][x])

print("TOTAL NUMBER OF ONLINE CUSTOMERS: "+str(len(customerData["Number"])))
print("PAYMENT REQUEST SENT TO "+str(count)+" customers")
print("PAYMENT REQUEST IGNORED FOR "+str(len
(customerData["Number"])-count)+" paid customers")
print("TOTAL AMOUNT COLLECTED VIA ONLINE: Rs."+str(paid))
print("TOTAL AMOUNT PENDING: Rs."+str(unpaid))
        