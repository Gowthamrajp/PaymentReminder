import os
import logging
from datetime import datetime
import pandas as pd
import pywhatkit
import json
import time
from typing import Dict, List

# Configure logging
logging.basicConfig(
    filename='payment_reminder.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PaymentReminder:
    def __init__(self):
        self.config = self._load_config()
        self.stats = {
            'online': {'total': 0, 'paid': 0, 'unpaid_amount': 0, 'paid_amount': 0},
            'offline': {'total': 0, 'paid': 0, 'unpaid_amount': 0, 'paid_amount': 0}
        }
        self.failed_messages: List[Dict] = []
        
    def _load_config(self):
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            self._validate_config(config)
            return config
        except FileNotFoundError:
            logging.error("config.json not found")
            raise
            
    def _validate_config(self, config: Dict) -> None:
        """Validate configuration parameters"""
        required_fields = ['csv_path', 'admin_phone']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required config field: {field}")
        
        if not config['admin_phone'].startswith('+'):
            config['admin_phone'] = f"+{config['admin_phone']}"

    def _validate_customer_data(self, df: pd.DataFrame) -> None:
        """Validate customer data format"""
        required_columns = ['Number', 'Name', 'Amount', 'Cycle', 'Mode', 'Status']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

    def get_customer_data(self) -> pd.DataFrame:
        """Read and validate customer data from local CSV file"""
        try:
            df = pd.read_csv(self.config['csv_path'])
            self._validate_customer_data(df)
            logging.info(f"Successfully loaded {len(df)} records from CSV")
            return df
        except Exception as e:
            logging.error(f"Error reading CSV file: {str(e)}")
            raise

    def send_whatsapp_message(self, number: int, name: str, amount: float, cycle: str) -> bool:
        """Send WhatsApp message with error handling"""
        message = (
            f"Dear Customer Good Afternoon,\n"
            f"Gentle Reminder\n"
            f"Kindly Please pay Cable TV amount for {cycle} month Rs {amount} "
            f"via Gpay/Paytm/phonepay/WhatsApp\n\n"
            f"9444047656 ( Pandian )  Rs {amount} \n"
            f"Please Send screen shot of payment receipt if possible\n\n"
            f"Ignore if Paid \n\n"
            f"Thank you for your kind Co-operation.Have a Nice day🙏"
        )

        try:
            pywhatkit.sendwhatmsg_instantly(
                f"+91{str(round(number))}",
                message,
                15,
                True,
                3
            )
            logging.info(f"Reminder sent to {name}")
            return True
        except Exception as e:
            logging.error(f"Error sending message to {name}: {str(e)}")
            self.failed_messages.append({
                'name': name,
                'number': number,
                'amount': amount,
                'cycle': cycle,
                'error': str(e)
            })
            return False

    def process_customer(self, row: pd.Series) -> None:
        """Process individual customer data"""
        mode = str(row['Mode']).lower().strip()
        if mode in ['gpay', 'g-pay', 'google pay']:
            mode = 'online'
        elif mode not in ['online', 'offline']:
            logging.warning(f"Unknown payment mode '{mode}' for customer {row['Name']}, defaulting to offline")
            mode = 'offline'
        
        status = str(row['Status']).lower().strip()
        amount = float(row['Amount'])

        # Update statistics
        self.stats[mode]['total'] += 1
        if status == 'paid':
            self.stats[mode]['paid'] += 1
            self.stats[mode]['paid_amount'] += amount
        else:
            self.stats[mode]['unpaid_amount'] += amount
            if mode == 'online':
                self.send_whatsapp_message(
                    row['Number'],
                    row['Name'],
                    amount,
                    row['Cycle']
                )

    def retry_failed_messages(self) -> None:
        """Retry sending failed messages"""
        if not self.failed_messages:
            return
            
        logging.info(f"Retrying {len(self.failed_messages)} failed messages")
        retry_messages = self.failed_messages.copy()
        self.failed_messages.clear()
        
        for msg in retry_messages:
            time.sleep(5)  # Short delay between retries
            self.send_whatsapp_message(
                msg['number'],
                msg['name'],
                msg['amount'],
                msg['cycle']
            )

    def generate_report(self) -> None:
        """Generate and send summary report"""
        report = self._create_report_message()
        try:
            # Send report to admin number
            pywhatkit.sendwhatmsg_instantly(
                self.config['admin_phone'],
                report,
                15,
                True,
                3
            )
            logging.info("Summary report sent successfully")
            
            # Save report to a file
            report_file = f"report_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(report_file, 'w') as f:
                f.write(report)
                if self.failed_messages:
                    f.write("\n\nFailed Messages:\n")
                    for msg in self.failed_messages:
                        f.write(f"\n{msg['name']} ({msg['number']}): {msg['error']}")
            
            logging.info(f"Report saved to {report_file}")
            
        except Exception as e:
            logging.error(f"Error sending summary report: {str(e)}")

    def _create_report_message(self) -> str:
        """Create formatted report message"""
        online = self.stats['online']
        offline = self.stats['offline']
        
        return (
            f"\n\nDAILY COLLECTION REPORT {datetime.now().strftime('%Y-%m-%d')}\n"
            f"----------------------------------------\n"
            f"TOTAL CUSTOMERS: {online['total'] + offline['total']}\n"
            f"ONLINE CUSTOMERS: {online['total']}\n"
            f"OFFLINE CUSTOMERS: {offline['total']}\n\n"
            f"PAYMENT REQUESTS SENT: {online['total'] - online['paid']}\n"
            f"IGNORED (PAID/OFFLINE): {online['paid'] + offline['total']}\n\n"
            f"ONLINE COLLECTIONS:\n"
            f"Collected: ₹{online['paid_amount']} ({online['paid']} customers)\n"
            f"Pending: ₹{online['unpaid_amount']} ({online['total'] - online['paid']} customers)\n\n"
            f"OFFLINE COLLECTIONS:\n"
            f"Collected: ₹{offline['paid_amount']} ({offline['paid']} customers)\n"
            f"Pending: ₹{offline['unpaid_amount']} ({offline['total'] - offline['paid']} customers)\n\n"
            f"TOTAL EXPECTED: ₹{sum(s['paid_amount'] + s['unpaid_amount'] for s in self.stats.values())}\n"
            f"TOTAL COLLECTED: ₹{sum(s['paid_amount'] for s in self.stats.values())}\n"
            f"TOTAL PENDING: ₹{sum(s['unpaid_amount'] for s in self.stats.values())}"
        )

    def run(self) -> None:
        """Main execution method"""
        try:
            logging.info("Starting payment reminder process")
            df = self.get_customer_data()
            
            total_records = len(df)
            for idx, row in df.iterrows():
                self.process_customer(row)
                if (idx + 1) % 10 == 0:
                    logging.info(f"Processed {idx + 1}/{total_records} records")
            
            if self.failed_messages:
                self.retry_failed_messages()
                
            self.generate_report()
            logging.info("Payment reminder process completed successfully")
            
        except Exception as e:
            logging.error(f"Error in main execution: {str(e)}")
            raise

if __name__ == "__main__":
    reminder = PaymentReminder()
    reminder.run()
