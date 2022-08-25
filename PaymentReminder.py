import pandas as pd
import os;
import pywhatkit

global onlineCustomerCount
onlineCustomerCount=0 
global onlinePaidCount 
onlinePaidCount=0
global onlineUnpaidAmount 
onlineUnpaidAmount=0
global onlinePaidAmount
onlinePaidAmount=0
global offlineCustomerCount 
offlineCustomerCount=0
global offlinePaidCount 
offlinePaidCount=0
global offlineUnpaidAmount 
offlineUnpaidAmount=0
global offlinePaidAmount
offlinePaidAmount=0
customerData = pd.read_csv (os.getcwd()+"\CustomerData.csv")  

def sender(number,name,amount,cycle,isPaid,mode):
    global onlineCustomerCount 
    global onlinePaidCount 
    global onlineUnpaidAmount 
    global onlinePaidAmount

    global offlineCustomerCount 
    global offlinePaidCount 
    global offlineUnpaidAmount 
    global offlinePaidAmount
    

    if(mode=="offline"):
        offlineCustomerCount=offlineCustomerCount+1
        if(isPaid=="paid"):
            offlinePaidCount=offlinePaidCount+1
            offlinePaidAmount =offlinePaidAmount +amount
        else:
            offlineUnpaidAmount =offlineUnpaidAmount +amount
    else:
        onlineCustomerCount=onlineCustomerCount+1
        if(isPaid!="paid"):        
            onlineUnpaidAmount= onlineUnpaidAmount+amount
            pywhatkit.sendwhatmsg_instantly("+"+str(number),"Dear Customer,\nPlease pay Cable TV amount for "+cycle+" month Rs"+str(amount)+"via Gpay/Paytm/phonepay/WhatsApp\n\n9444047656 ( Pandian )  Rs "+str(amount)+" \nPlease Send screen shot of payment receipt if possible\n\nIgnore if Paid \n\nThank you for your kind Co-operation.Have a Nice day"+"\U0001F64F",15,True,3)
            print(str(x+1)+". Reminder sent to "+name )
        else:
            onlinePaidAmount=onlinePaidAmount+amount
            onlinePaidCount=onlinePaidCount+1
    

for x in range(0,len(customerData["Number"])):
        sender(customerData["Number"][x], customerData["Name"][x], customerData["Amount"][x], customerData["Cycle"][x] , customerData["Status"][x], customerData["Mode"][x])

print("TOTAL NUMBER OF CUSTOMERS: "+str(len(customerData["Number"])))
print("TOTAL NUMBER OF ONLINE CUSTOMERS: "+str(onlineCustomerCount)) 
print("TOTAL NUMBER OF OFFLINE CUSTOMERS: "+str(offlineCustomerCount))

print("PAYMENT REQUEST SENT TO "+str(onlineCustomerCount-onlinePaidCount)+" online customers")
print("PAYMENT REQUEST IGNORED FOR "+str(onlinePaidCount)+" paid Online customers and "+str(offlineCustomerCount)+" Offline customers" )

print("TOTAL AMOUNT COLLECTED VIA ONLINE: Rs."+str(onlinePaidAmount)+"from"+str(onlinePaidCount)+ "Customers -> avg:"+str(onlinePaidAmount/onlinePaidCount))
print("TOTAL AMOUNT PENDING ONLINE: Rs."+str(onlineUnpaidAmount)+"from"+str(onlineCustomerCount-onlinePaidCount)+ "Customers -> avg:"+str(onlineUnpaidAmount/onlineCustomerCount-onlinePaidCount))

print("TOTAL AMOUNT COLLECTED VIA OFFLINE: Rs."+str(offlinePaidAmount)+"from"+str(offlinePaidCount)+ "Customers -> avg:"+str(offlinePaidAmount/offlinePaidCount))
print("TOTAL AMOUNT PENDING OFFLINE: Rs."+str(offlineUnpaidAmount)+"from"+str(offlineCustomerCount-offlinePaidCount)+ "Customers -> avg:"+str(offlineUnpaidAmount/offlineCustomerCount-offlinePaidCount))    