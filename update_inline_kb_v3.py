import os

file_path = 'app/keyboards/inline.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update get_launch_planned_kb
new_launch_kb = """def get_launch_planned_kb() -> InlineKeyboardMarkup:
    \"\"\"Generates an inline keyboard to ask if launch is planned for 'Not Working' mode.\"\"\"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Так планується", callback_data="launch_planned_yes"),
                InlineKeyboardButton(text="Ні не планується", callback_data="launch_planned_no")
            ],
            [InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")]
        ]
    )"""

# 2. Update get_power_type_kb to include "Пропустити"
new_power_kb = """def get_power_type_kb() -> InlineKeyboardMarkup:
    \"\"\"Generates an inline keyboard to select power type.\"\"\"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Планова", callback_data="power_type:Планова"),   
                InlineKeyboardButton(text="Поточна", callback_data="power_type:Поточна")    
            ],
            [InlineKeyboardButton(text="Пропустити", callback_data="power_type:skip")],
            [InlineKeyboardButton(text="Відміна", callback_data="cancel_checklist")]
        ]
    )"""

# Safe replace using markers
def replace_func(text, func_name, new_body):
    start_marker = f"def {func_name}()"
    if start_marker not in text:
        return text
    
    start_pos = text.find(start_marker)
    # Find the end of the function (assuming next def or end of file)
    end_pos = text.find("def ", start_pos + 10)
    if end_pos == -1:
        return text[:start_pos] + new_body + "\n"
    else:
        return text[:start_pos] + new_body + "\n\n" + text[end_pos:]

content = replace_func(content, "get_launch_planned_kb", new_launch_kb)
content = replace_func(content, "get_power_type_kb", new_power_kb)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print("Inline KB updated")
