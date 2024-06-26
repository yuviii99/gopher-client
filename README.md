# Indexing a Gopher server

The directory contains a python script `gopher_client.py` to crawl the host `your.gopher.host` on port `70`.

## Setup and Run the client

Change `your.gopher.host` in `gopher_client.py` to your specific gopher host server address.

To run the gopher client, run the following command in your terminal: 

```bash
python3 gopher_client.py
```

The client will start crawling the gopher server and prints all the request in the STDOUT.
All the binary and text files will be downloaded inside `gopher_server_files` directory.

## Server Statistics Logs

At the end of the run, the client will print all the server statistics in STDOUT and also store them inside
`server_stats.txt` file in the directory.

These statistics include:

- The number of Gopher directories on the server.
- The number, and a list of all simple text files (full path)
- The number, and a list of all binary (i.e. non-text) files (full path)
- The contents of the smallest text file.
- The size of the largest text file.
- The size of the smallest and the largest binary files.
- The number of unique invalid references (those with an “error” type)
- A list of external servers (those on a different host and/or port) that were referenced, and
   whether or not they were "up" (i.e. whether they accepted a connection on the specified port).
- Any references that have “issues/errors”, that code needs to explicitly deal with.

## Count items and handle issues/errors

- The client will only count files once they are successfully downlaoded from the server.
- The client only downloads the files of size upto 1000000 bytes (~ 1 MB), if file size exceeds this limit, the download is aborted.
- If the file is taking too long to respond, the download request will timeout after 6 seconds.
