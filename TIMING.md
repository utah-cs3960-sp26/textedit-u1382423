The following are the timing measurements for opening files of various sizes in the text editor.

## Initial Measurements (maximum frame time)

### small.txt

To open - 3 ms
To quickly scroll - 2.5 ms
To quickly scroll far away (with scroll bar) - 4 ms
To find and replace (19) - 3 ms
Memory usage - negligable

### medium.txt

To open - 22 ms
To quickly scroll - 3 ms
To quickly scroll far away (with scroll bar) - 4 ms
To find and replace (1186) - 18 ms
Memory usage - negligable

### large.txt

To open - 8188 ms
To quickly scroll - 9 ms
To quickly scroll far away (with scroll bar) - 23 ms
To find and replace (668753) - 8821 ms
Memory usage - 1.5 GiB 


## Submission Measurements

### small.txt

To open - 8 milliseconds
To quickly scroll - 6 milliseconds
To quickly scroll far away (with scroll bar) - 6 milliseconds
To find and replace (19) - 11 milliseconds
Memory usage - negligable

### medium.txt

To open - 17 milliseconds (1 dropped frames)
To quickly scroll - 7 milliseconds
To quickly scroll far away (with scroll bar) - 12 milliseconds
To find and replace (1186) - 28 milliseconds (2 dropped frames)
Memory usage - 0.1 GiB

### large.txt

To open -  30 milliseconds (6 dropped frames)
To quickly scroll - 16 milliseconds
To quickly scroll far away (with scroll bar) - 78 milliseconds (20 dropped frames)
To find and replace (668753) - 600 milliseconds (20 dropped frames)
Memory usage - 1.5 GiB 

#### Memory note:
I was saving a file document in memory as long as that file instance was being referenced. So even if I closed a file, that file document may (and was) still stored in memory.
