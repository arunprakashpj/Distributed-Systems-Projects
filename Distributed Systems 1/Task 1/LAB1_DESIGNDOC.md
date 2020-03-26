## General info

We implement the global 'board' variable data structure as array of hashes.
Each entry is a row or cell in the board. A new hash entry is appended to 'board
when user submit new entry. Modify/delete also triggers a change to the 'board'
variable.

## Propagation mechanism

Everytime a user add/modify/delete any entry on a vessel, that particular vessel will
broadcast the changes to other vessels via HTTP POST. The other vessels will then
capture the changes and modify the 'board' data structure accordingly.

The modify and delete (X) button in the UI will trigger a POST to 
/propagate/<action>/<entry_id>. `propagation_received` function will
capture this user action and propagate changes to other vessel as stated above.
