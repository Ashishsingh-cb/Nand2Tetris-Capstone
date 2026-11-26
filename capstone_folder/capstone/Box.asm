
// Box.asm
// Nand2Tetris Capstone Project
// Roll Number: 2501410031
// K = 31
//
// Box specifications:
// Starting row = 31
// Height = 20 rows
// Width = 64 pixels = 4 screen words
// Left edge = 0 pixels
// Starting address = SCREEN + (32 * 31) = 17376
//
// Key pressed  -> Black box
// Key released -> Erase box

(LOOP)
    // Check keyboard
    @KBD
    D=M
    @PRESSED
    D;JNE

    // No key pressed: erase box
    @fill
    M=0
    @PAINT
    0;JMP

(PRESSED)
    // Key pressed: draw black box
    @fill
    M=-1

(PAINT)
    // Set starting screen address
    @17376
    D=A
    @addr
    M=D

    // Set box height to 20 rows
    @20
    D=A
    @count
    M=D

(ROW)
    // Get drawing pattern (black or white)
    @fill
    D=M

    // Draw first word
    @addr
    A=M
    M=D

    // Draw second word
    A=A+1
    M=D

    // Draw third word
    A=A+1
    M=D

    // Draw fourth word
    A=A+1
    M=D

    // Move to the next screen row (32 words)
    @32
    D=A
    @addr
    M=D+M

    // Decrease row counter
    @count
    M=M-1
    D=M

    // Repeat until all 20 rows are drawn
    @ROW
    D;JGT

    // Check keyboard again
    @LOOP
    0;JMP
