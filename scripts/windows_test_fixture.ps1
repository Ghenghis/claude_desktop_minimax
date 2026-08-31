# Explicit disposable UI test. No files, network, process control or timers.
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$form = [Windows.Forms.Form]::new()
$form.Text = 'Claude MCP test fixture'
$form.Size = [Drawing.Size]::new(720, 300)
$form.StartPosition = [Windows.Forms.FormStartPosition]::CenterScreen
$heading = [Windows.Forms.Label]::new()
$heading.Text = 'Disposable Windows-MCP input test'
$heading.Location = [Drawing.Point]::new(25, 25)
$heading.AutoSize = $true
$inputBox = [Windows.Forms.TextBox]::new()
$inputBox.Name = 'AcceptanceInput'
$inputBox.AccessibleName = 'Acceptance input'
$inputBox.Location = [Drawing.Point]::new(25, 65)
$inputBox.Size = [Drawing.Size]::new(640, 30)
$verify = [Windows.Forms.Button]::new()
$verify.Text = 'Verify'
$verify.AccessibleName = 'Verify test input'
$verify.Location = [Drawing.Point]::new(25, 115)
$verify.Size = [Drawing.Size]::new(130, 40)
$result = [Windows.Forms.Label]::new()
$result.Text = 'Waiting for test input'
$result.AccessibleName = 'Test result'
$result.Location = [Drawing.Point]::new(25, 180)
$result.AutoSize = $true
$verify.Add_Click({
    $result.Text = if ($inputBox.Text -ceq 'CLAUDE_WINDOWS_TEST_PASSED') { 'CLAUDE_WINDOWS_TEST_PASSED' } else { 'Input did not match' }
    $result.AccessibleName = $result.Text
})
$form.Controls.AddRange(@($heading, $inputBox, $verify, $result))
try { [void]$form.ShowDialog() } finally { $form.Dispose() }
