import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import pywhatkit
import json
import time
import hashlib
from typing import Dict, List
from openpyxl import load_workbook

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
        self.inactive_customers: List[Dict] = []
        self.paid_smartcards: List[str] = []
        self.reminder_history = self._load_reminder_history()
        
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
        required_fields = ['excel_path', 'admin_phones', 'sheet_name']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required config field: {field}")
        
        # Convert to list if it's a string
        if isinstance(config['admin_phones'], str):
            config['admin_phones'] = [config['admin_phones']]
            
        # Ensure all phone numbers start with +
        for i, phone in enumerate(config['admin_phones']):
            if not phone.startswith('+'):
                config['admin_phones'][i] = f"+{phone}"
                
        # Set default time difference if not provided
        if 'time_difference_hours' not in config:
            config['time_difference_hours'] = 24
            logging.info("Using default time difference of 24 hours")

    def _load_reminder_history(self) -> Dict:
        """Load reminder history from JSON file"""
        history_file = 'reminder_history.json'
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading reminder history: {str(e)}")
                return {}
        return {}
    
    def _save_reminder_history(self) -> None:
        """Save reminder history to JSON file"""
        try:
            with open('reminder_history.json', 'w') as f:
                json.dump(self.reminder_history, f, indent=2)
            logging.info("Reminder history saved successfully")
        except Exception as e:
            logging.error(f"Error saving reminder history: {str(e)}")
    
    def _get_customer_data(self, row: pd.Series) -> Dict:
        """Extract important customer data in human-readable format"""
        important_fields = ['Name', 'Amount', 'Cycle', 'Status']
        return {field: str(row.get(field, '')) for field in important_fields}

    def _validate_customer_data(self, df: pd.DataFrame) -> None:
        """Validate customer data format"""
        required_columns = ['Number', 'Name', 'Amount', 'Cycle', 'Mode', 'Status']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
            
        # Log warning if smart card columns are missing but don't raise error
        smart_card_columns = ['Smartcard Number', 'Secondry Smartcard Number']
        missing_smartcard = [col for col in smart_card_columns if col not in df.columns]
        if missing_smartcard:
            logging.warning(f"Missing smartcard columns: {missing_smartcard}")

    def get_customer_data(self) -> pd.DataFrame:
        """Read and validate customer data from Excel file"""
        try:
            # Read Excel file
            df = pd.read_excel(
                self.config['excel_path'],
                sheet_name=self.config['sheet_name']
            )
            
            # Clean up any empty rows
            df = df.dropna(how='all')
            
            
            self._validate_customer_data(df)
            logging.info(f"Successfully loaded {len(df)} records from Excel")
            return df
        except Exception as e:
            logging.error(f"Error reading Excel file: {str(e)}")
            raise

    def should_send_reminder(self, customer_number: str, current_data: Dict) -> bool:
        """Determine if a reminder should be sent based on date and data changes"""
        customer_key = str(customer_number)
        current_time = datetime.now()
        current_date = current_time.date()
        
        # If no previous reminder has been sent to this customer
        if customer_key not in self.reminder_history:
            return True
        
        last_reminded = datetime.fromisoformat(self.reminder_history[customer_key]['timestamp'])
        last_reminded_date = last_reminded.date()
        previous_data = self.reminder_history[customer_key]['data']
        
        # If the last reminder was sent on a different day (not today)
        if current_date > last_reminded_date:
            logging.info(f"Sending reminder to {customer_number} - last reminder was on {last_reminded_date}, sending new one today")
            return True
        
        # If it's the same day, only send if data has changed
        if previous_data != current_data:
            logging.info(f"Sending reminder to {customer_number} - data changed since last reminder")
            return True
            
        logging.info(f"Skipping reminder for {customer_number} - already sent today ({current_date})")
        return False

    def update_reminder_history(self, customer_number: str, customer_data: Dict) -> None:
        """Update the reminder history for a customer"""
        customer_key = str(customer_number)
        self.reminder_history[customer_key] = {
            'timestamp': datetime.now().isoformat(),
            'data': customer_data
        }

    def send_whatsapp_message(self, number_value, name: str, amount: float, cycle: str, mode: str) -> bool:
        """Send WhatsApp message with error handling to one or multiple numbers"""
        # Check for missing or invalid phone number
        if pd.isna(number_value):
            logging.error(f"Cannot send message to {name}: Missing phone number")
            self.failed_messages.append({
                'name': name,
                'number': 'Missing',
                'amount': amount,
                'cycle': cycle,
                'mode': mode,
                'error': 'Missing phone number'
            })
            return False

        # Check if mode is bank transfer related
        mode_lower = mode.lower().strip()
        is_bank_transfer = any(term in mode_lower for term in ['bank', 'transfer', 'neft', 'imps', 'rtgs'])
        
        base_message = (
            f"*📺 CABLE TV PAYMENT REMINDER 📺*\n\n"
            f"Dear Customer,\n\n"
            f"We request you to kindly pay your Cable TV subscription.\n"
            f"💰 *Amount Due: ₹{amount}*\n"
            f"📅 *Period: {cycle}*\n\n"
            f"*Payment Options:*\n"
            f"📱 *UPI/Mobile Payment:*\n"
            f"   9444047656 (Pandian)\n"
            f"   (GPay/PhonePe/Paytm/WhatsApp)\n\n"
        )
        
        bank_details = (
            f"🏦 *Bank Transfer:*\n"
            f"   Account holder: GOWTHAM RAJ\n"
            f"   A/C No: 50100371282075\n"
            f"   Bank: HDFC BANK\n"
            f"   Branch: VALSARAVAKKAM\n"
            f"   IFSC: HDFC0000024\n\n"
        )
        
        footer = (
            f"📸 Please share a screenshot after payment.\n\n"
            f"_Note: Please ignore if already paid. This is an automated message._\n\n"
            f"Thank you for your continued support! 🙏\n"
            f"- The Best Cable Vision"
        )
        
        # Include bank details only for bank transfer payment modes
        if is_bank_transfer:
            message = base_message + bank_details + footer
        else:
            message = base_message + footer

        # Parse semicolon-separated phone numbers
        numbers = str(number_value).split(';')
        success = False
        
        for number in numbers:
            number = number.strip()
            if not number:
                continue
                
            try:
                pywhatkit.sendwhatmsg_instantly(
                    f"+91{str(round(float(number)))}",
                    message,
                    15,
                    True,
                    3
                )
                logging.info(f"Reminder sent to {name} at number {number}")
                success = True
                time.sleep(3)  # Add a short delay between messages to multiple numbers
            except Exception as e:
                logging.error(f"Error sending message to {name} at number {number}: {str(e)}")
                self.failed_messages.append({
                    'name': name,
                    'number': number,
                    'amount': amount,
                    'cycle': cycle,
                    'mode': mode,
                    'error': str(e)
                })
        
        return success

    def collect_smartcards(self, row: pd.Series) -> List[str]:
        """Extract smartcard numbers from a customer row"""
        smartcards = []
        if 'Smartcard Number' in row and pd.notna(row['Smartcard Number']):
            smartcards.append(str(row['Smartcard Number']).strip())
        if 'Secondry Smartcard Number' in row and pd.notna(row['Secondry Smartcard Number']):
            smartcards.append(str(row['Secondry Smartcard Number']).strip())
        return [card for card in smartcards if card]  # Filter out empty strings

    def process_customer(self, row: pd.Series) -> None:
        """Process individual customer data"""
        # Check for missing or NaN phone number
        if pd.isna(row.get('Number')):
            logging.warning(f"Skipping customer with missing phone number: {row.get('Name', 'Unknown')}")
            return
            
        # Check if customer is inactive - do this early to exclude from calculations
        is_inactive = False
        status = str(row['Status']).lower().strip()
        
        # Check Status column
        if status.lower() in ['inactive', 'deactivate', 'cancelled']:
            is_inactive = True
            
        # Also check Customer Status column if it exists
        if 'Customer Status' in row and pd.notna(row['Customer Status']):
            customer_status = str(row['Customer Status']).lower().strip()
            if customer_status in ['inactive', 'deactivate', 'cancelled', 'closed']:
                is_inactive = True
                logging.info(f"Found inactive customer via Customer Status column: {row['Name']}")
        
        # Collect smartcard numbers for inactive customers but exclude from stats
        if is_inactive:
            smartcards = self.collect_smartcards(row)
            self.inactive_customers.append({
                'name': row['Name'],
                'number': row['Number'],
                'smartcards': smartcards if smartcards else ['No smartcard']
            })
            logging.info(f"Added inactive customer for deactivation: {row['Name']} with smartcards: {smartcards}")
            return  # Skip the rest of processing for inactive customers
            
        # Check if reminder should be skipped based on SkipUntil column
        if 'SkipUntil' in row and pd.notna(row['SkipUntil']):
            try:
                # Try to parse the date - should be in DD/MM/YYYY format
                skip_until_date = pd.to_datetime(row['SkipUntil'], format='%d/%m/%Y').date()
                current_date = datetime.now().date()
                
                if current_date <= skip_until_date:
                    logging.info(f"Skipping reminder for {row.get('Name', 'Unknown')} until {skip_until_date}")
                    return
            except Exception as e:
                logging.warning(f"Invalid date format in SkipUntil for {row.get('Name', 'Unknown')}: {str(e)}")
            
        mode = str(row['Mode']).lower().strip()
        original_mode = row['Mode']  # Keep original mode for message customization
        if mode in ['gpay', 'g-pay', 'google pay', 'phonepe', 'phone pe', 'phonepay', 'bank transfer', 'bank', 'transfer', 'neft', 'imps', 'rtgs', 'upi']:
            mode = 'online'
        elif mode not in ['online', 'offline']:
            logging.warning(f"Unknown payment mode '{mode}' for customer {row['Name']}, defaulting to offline")
            mode = 'offline'
        
        # Handle missing or non-numeric amount values
        try:
            if pd.isna(row['Amount']):
                amount = 0
                logging.warning(f"Missing amount for customer {row['Name']}, using 0")
            else:
                amount = float(row['Amount'])
        except (ValueError, TypeError):
            logging.warning(f"Invalid amount format for customer {row['Name']}, using 0")
            amount = 0
            
        # Get primary number for reminder history key (first number or full value)
        number_value = row['Number']
        numbers = str(number_value).split(';')
        primary_number = numbers[0].strip() if numbers else str(number_value)
        
        try:
            customer_number = str(round(float(primary_number)))
        except ValueError:
            logging.warning(f"Invalid phone number format for {row.get('Name', 'Unknown')}: {primary_number}")
            customer_number = hashlib.md5(str(primary_number).encode()).hexdigest()[:10]
            
        customer_data = self._get_customer_data(row)
        
        # Get smartcard numbers for this customer
        smartcards = self.collect_smartcards(row)

        # Update statistics
        self.stats[mode]['total'] += 1
        if status == 'paid':
            self.stats[mode]['paid'] += 1
            self.stats[mode]['paid_amount'] += amount
            
            # Add smartcards from paid customers to the paid_smartcards list
            self.paid_smartcards.extend(smartcards)
            
        else:
            self.stats[mode]['unpaid_amount'] += amount
            if mode == 'online':
                # Check if we should send a reminder
                if self.should_send_reminder(customer_number, customer_data):
                    if self.send_whatsapp_message(
                        row['Number'],
                        row['Name'],
                        amount,
                        row['Cycle'],
                        original_mode  # Pass the original mode to customize the message
                    ):
                        # Update reminder history only if message was sent successfully
                        self.update_reminder_history(customer_number, customer_data)
                else:
                    logging.info(f"Skipping reminder for {row['Name']} - recent reminder with no data change")

    def retry_failed_messages(self) -> None:
        """Retry sending failed messages"""
        if not self.failed_messages:
            return
            
        logging.info(f"Retrying {len(self.failed_messages)} failed messages")
        retry_messages = self.failed_messages.copy()
        self.failed_messages.clear()
        
        for msg in retry_messages:
            time.sleep(5)  # Short delay between retries
            
            if self.send_whatsapp_message(
                msg['number'],
                msg['name'],
                msg['amount'],
                msg['cycle'],
                msg['mode']
            ):
                # Update reminder history for successfully retried messages
                # If the number is a string like 'Missing', handle it appropriately
                if isinstance(msg['number'], str) and msg['number'] == 'Missing':
                    continue
                    
                # Handle either single number or semicolon-separated numbers
                numbers = str(msg['number']).split(';')
                primary_number = numbers[0].strip() if numbers else str(msg['number'])
                try:
                    customer_number = str(round(float(primary_number)))
                    # Create readable data for retried messages
                    customer_data = {
                        'Name': msg['name'],
                        'Amount': str(msg['amount']),
                        'Cycle': msg['cycle'],
                        'Status': 'unpaid'  # Assuming unpaid since we're sending a reminder
                    }
                    self.update_reminder_history(customer_number, customer_data)
                except (ValueError, TypeError):
                    logging.warning(f"Could not process number for reminder history: {primary_number}")

    def generate_report(self) -> None:
        """Generate and send summary report"""
        report = self._create_report_message()
        report_file = f"report_{datetime.now().strftime('%Y%m%d')}.txt"
        
        try:
            # Send report to all admin numbers
            for admin_phone in self.config['admin_phones']:
                pywhatkit.sendwhatmsg_instantly(
                    admin_phone,
                    report,
                    15,
                    True,
                    3
                )
                logging.info(f"Summary report sent successfully to {admin_phone}")
                time.sleep(5)  # Add delay between messages
            
            # Save report to a file
            with open(report_file, 'w') as f:
                f.write(report)
                
                # Add failed messages to report file
                if self.failed_messages:
                    f.write("\n\nFailed Messages:\n")
                    for msg in self.failed_messages:
                        f.write(f"\n{msg['name']} ({msg['number']}): {msg['error']}")
                
                # Add paid smartcards to report file
                if self.paid_smartcards:
                    f.write("\n\nPaid Customer Smartcards:\n")
                    f.write("----------------------------------------\n")
                    f.write(f"{','.join(self.paid_smartcards)}\n")
                    f.write("----------------------------------------\n")
                
                # Add inactive customers to report file
                if self.inactive_customers:
                    f.write("\n\nInactive Customers to Deactivate:\n")
                    f.write("----------------------------------------\n")
                    for customer in self.inactive_customers:
                        f.write(f"\nName: {customer['name']}, Phone: {customer['number']}\n")
                        f.write(f"Smartcard Numbers: {','.join(customer['smartcards'])}\n")
                        f.write("----------------------------------------\n")
                    
                    # Add a simple comma-separated list of inactive smartcards
                    f.write("\nAll Inactive Smartcards (Comma-separated):\n")
                    f.write("----------------------------------------\n")
                    all_inactive_smartcards = []
                    for customer in self.inactive_customers:
                        all_inactive_smartcards.extend(customer['smartcards'])
                    f.write(f"{','.join(all_inactive_smartcards)}\n")
                    f.write("----------------------------------------\n")
            
            logging.info(f"Report saved to {report_file}")
            
        except Exception as e:
            logging.error(f"Error sending summary report: {str(e)}")

    def _create_report_message(self) -> str:
        """Create formatted report message"""
        online = self.stats['online']
        offline = self.stats['offline']
        
        # Ensure all numeric values are valid (not NaN)
        for mode_stats in [online, offline]:
            for key in ['paid_amount', 'unpaid_amount']:
                if pd.isna(mode_stats[key]):
                    mode_stats[key] = 0
                    
        # Calculate totals safely
        total_expected = online['paid_amount'] + online['unpaid_amount'] + offline['paid_amount'] + offline['unpaid_amount']
        total_collected = online['paid_amount'] + offline['paid_amount']
        total_pending = online['unpaid_amount'] + offline['unpaid_amount']
        
        report = (
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
            f"TOTAL EXPECTED: ₹{total_expected}\n"
            f"TOTAL COLLECTED: ₹{total_collected}\n"
            f"TOTAL PENDING: ₹{total_pending}"
        )
        
        # Add paid smartcards - include all of them without limit
        if self.paid_smartcards:
            report += f"\n\nPAID CUSTOMER SMARTCARDS to be paid on SCV: {len(self.paid_smartcards)}"
            report += f"\n----------------------------------------"
            report += f"\n{','.join(self.paid_smartcards)}"
            report += f"\n----------------------------------------"
            
        # Add inactive customers - only show smartcard numbers, not customer details
        if self.inactive_customers:
            all_inactive_smartcards = []
            for customer in self.inactive_customers:
                all_inactive_smartcards.extend(customer['smartcards'])
                
            # Skip individual customer details, only show all smartcard numbers
            report += f"\n\nINACTIVE SMARTCARDS TO DEACTIVATE: {len(all_inactive_smartcards)}"
            report += f"\n----------------------------------------"
            report += f"\n{','.join(all_inactive_smartcards)}"
            report += f"\n----------------------------------------"
        
        return report

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
            
            # Save reminder history after successful run
            self._save_reminder_history()
            
            logging.info("Payment reminder process completed successfully")
            
        except Exception as e:
            logging.error(f"Error in main execution: {str(e)}")
            raise

if __name__ == "__main__":
    reminder = PaymentReminder()
    reminder.run()
