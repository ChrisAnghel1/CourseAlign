$secret = "coursealign_TmN3noCYfEdXdZZ667SiMwGCym1AUrb0jVSyRH6oSA"
$pdf = "C:\Users\chris\Downloads\CS_Textbooks\Introduction to Algorithms, Fourth Edition ( etc.) (Z-Library).pdf"

curl.exe -X POST "http://127.0.0.1:8000/index-textbook" `
  -H "Authorization: Bearer $secret" `
  -F "course_code=CP312" `
  -F "textbook_pdf=@$pdf"
