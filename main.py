#!/usr/bin/env python3

import json
import os
import argparse
import requests
from tabulate import tabulate
from colorama import Fore, Style, init
from dotenv import load_dotenv

init(autoreset=True) #Initialize Colorama
load_dotenv() #Load environment variables from .env file

NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID', '')
NOTION_TOKEN = os.getenv('NOTION_TOKEN', '')

class SSHConnectionManager:
    def __init__(self, config_file='~/cmd/ssh-manager/ssh_config.json'):
        # Expand user directory
        self.config_file = os.path.expanduser(config_file)
        self.connections = {}
        self.load_config()

    def load_config(self):
        """Load SSH connection configuration from a JSON file."""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as file:
                self.connections = json.load(file)
        else:
            self.connections = {}
    
    def refresh(self):
        """Load SSH connection configuration from Notion with sorted query and update the local config file."""
        headers = {
            'Authorization': f'Bearer {NOTION_TOKEN}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }

        # Define the query with sorts for "Type" and "Project"
        query = {
            "sorts": [
                {"property": "Type", "direction": "descending"},
                {"property": "Project", "direction": "ascending"}
            ]
        }

        try:
            # Request the data from Notion
            response = requests.post(f'https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query', headers=headers, json=query)
            response.raise_for_status()
        except requests.RequestException as e:
            print(Fore.RED + f"Error: Failed to fetch data from Notion. {e}")
            return

        try:
            results = response.json().get('results', [])
        except ValueError:
            print(Fore.RED + "Error: Failed to decode JSON response from Notion.")
            return

        connections = {}
        for page in results:
            properties = page.get('properties', {})

            # Extract properties with safer access methods
            project_property = properties.get('Project', {}).get('title', [])
            project = project_property[0].get('text', {}).get('content', '') if project_property else ''

            ssh_property = properties.get('SSH', {}).get('rich_text', [])
            ssh = ssh_property[0].get('text', {}).get('content', '') if ssh_property else ''

            type_property = properties.get('Type', {}).get('select', {})
            type_ = type_property.get('name', '').lower() if type_property else ''

            password_property = properties.get('password', {}).get('rich_text', [])
            password = password_property[0].get('text', {}).get('content', '') if password_property else ''

            # Use project and type as the key to avoid duplicates
            key = f"{project}@{type_}"

            # Create connection entry
            connections[key] = {
                'type': type_,
                'project': project,
                'ssh_command': ssh,
                'password': password  # If you want to store the password (use with caution)
            }

        try:
            # Update the local SSH config file
            with open(self.config_file, 'w') as file:
                json.dump(connections, file, indent=4)
            self.connections = connections
            print(Fore.GREEN + "Data updated successfully!")
        except IOError as e:
            print(Fore.RED + f"Error: Failed to write to the configuration file. {e}")
        except Exception as e:
            print(Fore.RED + f"Unexpected error: {e}")

    def list_connections(self):
        if self.connections:
            table = []
            for idx, (name, details) in enumerate(self.connections.items(), 1):
                # Extracting relevant information from the details
                project = details['project']
                ssh_command = details['ssh_command']
                connection_type = details['type']
                password = details['password']
                
                table.append([idx, project, connection_type, f"{Fore.CYAN}{ssh_command}{Style.RESET_ALL}", password])
            
            headers = ["No", "Project", "Type", "SSH Command", "Password"]
            print(tabulate(table, headers=headers, tablefmt="rounded_grid"))

            # Adding a newline before the input prompt
            print()

            # Prompt user to select a connection
            try:
                index = int(input("Enter the " + Fore.CYAN + "number" + Style.RESET_ALL + " of the connection to run the SSH command: "))
                connection = list(self.connections.values())[index - 1]
                confirm = input(f"Are you sure you want to run the command for {Fore.YELLOW}{connection['project']}@{connection['type']}{Style.RESET_ALL}? Press Enter to confirm or Ctrl+C to cancel: ")
                if confirm == '':
                    print(Fore.GREEN + "Command executing..." + Style.RESET_ALL)
                    os.system(connection['ssh_command'])
                else:
                    print(Fore.RED + "Command execution canceled.")
            except (IndexError, ValueError):
                print(Fore.RED + "Invalid index. Please enter a valid number.")
            except KeyboardInterrupt:
                print(Fore.RED + "\nOperation canceled...\n")
        else:
            print(Fore.YELLOW + "No SSH connections available.")

def main():
    parser = argparse.ArgumentParser(description="Manage SSH connections.")
    parser.add_argument('command', nargs='?', choices=['list', 'refresh', 'help'], help="Command to execute")

    args = parser.parse_args()

    manager = SSHConnectionManager()

    if args.command is None or args.command == 'help':
        print(Fore.CYAN + "Available commands:")
        print("  list      - Show list & connect to your ssh")
        print("  refresh   - Refresh data from database")
        print("  help      - Show this help message")
        print("")
    elif args.command == 'list':
        manager.list_connections()
    elif args.command == 'refresh':
        manager.refresh()

if __name__ == '__main__':
    main()
