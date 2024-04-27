import socket
import os
import logging

# Global variables to store server statistics
DIRECTORIES_COUNT = 0
TEXT_FILES = []
BINARY_FILES = []
SMALLEST_TEXT_FILE_SIZE = float('inf')
SMALLEST_TEXT_FILE_CONTENT = None
LARGEST_TEXT_FILE_SIZE = 0
SMALLEST_BINARY_FILE_SIZE = float('inf')
LARGEST_BINARY_FILE_SIZE = 0
INVALID_REFERENCES = []
EXTERNAL_SERVERS = []
ISSUES = []

# Setup a logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

def fetch_server_response(host, port, selector):
    """
    Fetch the response from the given host and port for the specified selector
    
    Params:
        host(str): Hostname of the server.
        port(int): Port number of the server.
        selector(str): Selector used to get the response.
    
    Returns:
        bytes or None: Response recieved as a byte string or None if the request
        timed out or any other error occured.
    """
    global ISSUES
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(6)
        try:
            client.connect((host, port))
            client.sendall((selector + "\r\n").encode('utf-8'))
            response = b''
            downloaded_size = 0
            while True:
                data_chunk = client.recv(1024)
                if not data_chunk:
                    break
                downloaded_size += len(data_chunk)
                # Abort download if file size increases the max file size allowed.
                if downloaded_size > 1000000:
                    logger.error("Maximum file size reached. Aborting Download")
                    ISSUES.append(f"[ERROR] - {selector} on {host}:{port} is too long. Aborted download.")
                    return None
                response += data_chunk
            return response
        except socket.timeout as error:
            logger.error("Request timed out. Aborting download.")
            ISSUES.append(f"[ERROR] - {selector} on {host}:{port} is taking too long to respond. Aborted download.")
            return None
        except Exception as exception:
            logger.error(f"An unexpected error occured: {exception}")
            return None

def download_file(file, file_name):
    """
        Downloads the file from the server
        
        Params:
            file (dict): A dictionary containing the details of the file to download
            file_name (str): Name of the file to be downloaded.
    """
    
    global TEXT_FILES, BINARY_FILES, SMALLEST_TEXT_FILE_SIZE, SMALLEST_TEXT_FILE_CONTENT, LARGEST_TEXT_FILE_SIZE, SMALLEST_BINARY_FILE_SIZE, LARGEST_BINARY_FILE_SIZE, ISSUES
    
    file_host = file['host']
    file_port = file['port']
    file_selector = file['selector']
    file_type = file['item_type']
    
    if len(file_name) > 255:
        file_name = file_name[:255]
        ISSUES.append(f"[ISSUE] - {file_selector} on {file_host}:{file_port} name is too long. Sliced the file name to 255 chars and downloaded the file.")
    
    try:
        file_data = fetch_server_response(file_host, file_port, file_selector)
        if file_data is None:
            return
        if file_type == '9':  # Binary data
            file_size = len(file_data)
            if file_size < SMALLEST_BINARY_FILE_SIZE:
                SMALLEST_BINARY_FILE_SIZE = file_size
            if file_size > LARGEST_BINARY_FILE_SIZE:
                LARGEST_BINARY_FILE_SIZE = file_size
            mode = 'wb'
            if isinstance(file_data, str):  # If somehow the binary data is in str form, convert it
                file_data = file_data.encode('utf-8')
        elif file_type == '0':  # Assuming text data
            file_size = len(file_data)
            if file_size < SMALLEST_TEXT_FILE_SIZE:
                SMALLEST_TEXT_FILE_SIZE = file_size
                SMALLEST_TEXT_FILE_CONTENT = file_data.decode('utf-8', errors='replace')
            
            if file_size > LARGEST_TEXT_FILE_SIZE:
                LARGEST_TEXT_FILE_SIZE = file_size
            mode = 'w'
            if isinstance(file_data, bytes):  # Only decode if it's actually bytes
                file_data = file_data.decode('utf-8', errors='replace')
        
        # Create directory to download files if it doesn't exist.
        os.makedirs('comp3310_gopher_server_files', exist_ok=True)
        file_path = os.path.join('comp3310_gopher_server_files', file_name)
        
        with open(file_path, mode) as f:
            f.write(file_data)
        logger.info(f"[SUCCESSFUL] - File downloaded {file_name}")
        # Count them only after they're successfully downloaded.
        if file_type == '0':
            TEXT_FILES.append(file_selector)
        else:
            BINARY_FILES.append(file_selector)
    except socket.error as error:
        logger.error(f"[ERROR] - Network error occurred: {error}")
    except Exception as exception:
        logger.error(f"[ERROR] - An unexpected error occurres: {exception}")
        

def check_server_status(host, port):
    """
    Check whether the server on the given host and port is online or not.
    
    Params:
        host(str): Hostname of the server to check.
        port(int): Port number of the server.
    
    Returns:
        Boolean : A boolean value specifying the status of the server.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(5) # Timeout value incase the server is offline.
            client.connect((host, port))
            return True
    except:
        return False

def parse_response(response):
    """
        Function to parse the server reponse to get directories and files dictionaries to crawl
        and download.
        It also logs the error for invalid or error references.
        
        Params:
            response(str) : Response string recieved from the server.
            
        Returns:
            dirs (dict): Dictionary of the directories in the current gopher menu.
            files (dict): Dictionary of the files in the current gopher menu.
    """
    global DIRECTORIES_COUNT, INVALID_REFERENCES
    decoded_response = response.decode('utf-8').splitlines()
    dirs = []
    files = []
    
    for line in decoded_response:
        if line:
            items = line.split('\t')
            if len(items) >= 4:
                item_type = line[0]
                description = items[0][1:]
                selector = items[1]
                host = items[2]
                port = int(items[3])
                # Directories
                if item_type == '1':
                    DIRECTORIES_COUNT += 1
                    dirs.append(
                        {
                            'item_type': item_type,
                            'description': description,
                            'selector': selector,
                            'host': host,
                            'port': port
                        }
                    )
                # Binary/Text files
                elif item_type in ['0', '9']:
                    files.append(
                        {
                            'item_type': item_type,
                            'description': description,
                            'selector': selector,
                            'host': host,
                            'port': port
                        }
                    )
                # Invalid/Error references
                elif item_type == '3' or len(items) < 4:
                    INVALID_REFERENCES.append(line)
    
    return dirs, files
        

def crawl_server(host, port, visited_paths, original_host=None, selector=''):
    """
    Crawls the server from the given host and port with the selector
    
    Params:
        host(str): Hostname of the gopher server to crawl.
        port(int): Port number of the gopher server.
        visited_paths(set): A set to track visited paths to avoid loop
        original_host(str): Hostname from where crawling originated
        selector(string): Selector to use while connecting to the gopher server
    
    Returns:
        None
    
    Notes:
        This function recursively crawls the gopher server while keeping a track of
        visited paths to avoid getting stuck in a loop. If it encounters a reference to
        external host it skips crawling and check whether the external server is online
        or not. It downloads any text or binary file it encounters while crawling.
    """
    
    global EXTERNAL_SERVERS
    # Setup original host to the host when crawling is originated
    if original_host is None:
        original_host = host
    
    # Check for external host or a different port
    if host != original_host or port!=70:
        external_host = check_server_status(host, port)
        if external_host:
            logger.info(f"[EXTERNAL SERVER] - {host} on port {port} is online.")
            logger.info(f"[EXTERNAL SERVER] - Not crawling {host}")
            EXTERNAL_SERVERS.append(f"[EXTERNAL SERVER] - {host} on port: {port} is up!")
            return None
        else:
            logger.info(f"[EXTERNAL SERVER] - {host} on port {port} is offline.")
            EXTERNAL_SERVERS.append(f"[EXTERNAL SERVER] - {host} on port: {port} is offline!")
            return None
            
    # Get the response from the server for given selector
    server_response = fetch_server_response(host, port, selector)
    
    # Parse the response
    dirs, files = parse_response(server_response)
    
    # Download Files
    for file in files:
        if (file['host'], file['selector']) in visited_paths:
            return None
        visited_paths.add((file['host'], file['selector']))
        file_name = file['selector'].split('/')[-1]
        logger.info(f"[DOWNLOADING] - {file_name} from {file['host'] + file['selector']} on port: {file['port']}")
        download_file(file, file_name)
    
    # Recursively crawl directories
    for directory in dirs:
        if (directory['host'], directory['selector']) in visited_paths:
            return None
        visited_paths.add((directory['host'], directory['selector']))
        logger.info(f"[REQUEST] - {directory['host']}{directory['selector']} on port {directory['port']}")
        crawl_server(
            directory['host'],
            directory['port'],
            visited_paths,
            original_host,
            directory['selector']
        )

def print_server_stats():
    """
    Print server statistics to the console and write them to a file.
    """
    with open('server_stats.txt', 'w') as file:  # Open file in 'append' mode to add statistics at the end
        file.write("*************************************************************************\n")
        file.write("*                         Server Statistics                             *\n")
        file.write("*************************************************************************\n")
        file.write(f"Total number of directories on the server: {DIRECTORIES_COUNT}\n")
        file.write(f"Total number of simple text files: {len(TEXT_FILES)}\n")
        file.write("List of simple text files paths:\n")
        for text_file in TEXT_FILES:
            file.write(f"\t> {text_file}\n")
        file.write(f"Total number of binary files: {len(BINARY_FILES)}\n")
        file.write("List of binary files paths:\n")
        for binary_file in BINARY_FILES:
            file.write(f"\t> {binary_file}\n")
        file.write("Content of the smallest text file:\n")
        file.write(f"{SMALLEST_TEXT_FILE_CONTENT}\n")
        file.write(f"Size of largest text file: {LARGEST_TEXT_FILE_SIZE} bytes.\n")
        file.write(f"Size of smallest binary file: {SMALLEST_BINARY_FILE_SIZE} bytes.\n")
        file.write(f"Size of largest binary file: {LARGEST_BINARY_FILE_SIZE} bytes.\n")
        file.write("Invalid references:\n")
        for invalid_reference in INVALID_REFERENCES:
            file.write(f"\t> {invalid_reference}\n")
        file.write("List of referenced external servers with their status:\n")
        for external in EXTERNAL_SERVERS:
            file.write(f"\t> {external}\n")
        file.write("Other Issues/Errors:\n")
        for issue in ISSUES:
            file.write(f"\t> {issue}\n")

    # Print to console
    print("*************************************************************************")
    print("*                         Server Statistics                             *")
    print("*************************************************************************")
    print(f"Total number of directories on the server: {DIRECTORIES_COUNT}")
    print(f"Total number of simple text files: {len(TEXT_FILES)}")
    print("List of simple text files paths:")
    for text_file in TEXT_FILES:
        print('\t> ' + text_file)
    print(f"Total number of binary files: {len(BINARY_FILES)}")
    print("List of binary files paths:")
    for binary_file in BINARY_FILES:
        print('\t> ' + binary_file)
    print("Content of the smallest text file:")
    print(SMALLEST_TEXT_FILE_CONTENT)
    print(f"Size of largest text file: {LARGEST_TEXT_FILE_SIZE} bytes.")
    print(f"Size of smallest binary file: {SMALLEST_BINARY_FILE_SIZE} bytes.")
    print(f"Size of largest binary file: {LARGEST_BINARY_FILE_SIZE} bytes.")
    print("Invalid references:")
    for invalid_reference in INVALID_REFERENCES:
        print('\t> ' + invalid_reference)
    print("List of referenced external servers with their status:")
    for external in EXTERNAL_SERVERS:
        print('\t> ' + external)
    print("Other Issues/Errors:")
    for issue in ISSUES:
        print('\t> ' +issue)

        
def main():
    """
        Main function to run the program.
    """
    gopher_server_host = 'gopher.server.host'
    gopher_server_port = 70
    # A set to keep track of visited selectors
    visited_paths = set()
    crawl_server(gopher_server_host, gopher_server_port, visited_paths)
    logger.info(f"[SUCCESS] - Successfully crawled {gopher_server_host} on port: {gopher_server_port}")
    print_server_stats()

if __name__ == '__main__':
    main()
