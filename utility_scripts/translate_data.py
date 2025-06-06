import json
import os


def translate_directory_guild_files_to_single(
        directory_path: str,
        output_file_path: str
) -> None:
    """
    Translates all guild configuration files in a directory into a single JSON file.
    
    Args:
        directory_path (str): Path to the directory containing guild config files.
        output_file_path (str): Path to the output JSON file.
    """
    combined_data = {}

    for filename in os.listdir(directory_path):
        if filename.endswith(".json"):
            file_path = os.path.join(directory_path, filename)
            with open(file_path, 'r') as file:
                try:
                    data = json.load(file)
                    combined_data.update(data)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON from {file_path}: {e}")

    with open(output_file_path, 'w') as output_file:
        json.dump(combined_data, output_file, indent=4)

    print(f"Combined guild configurations saved to {output_file_path}")

if __name__ == "__main__":
    pass