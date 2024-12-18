import sys
import os
import os.path
import yaml
from PIL import Image
import subprocess
import uuid

def load_printers_config(config_file):
    """Load the printers.yml file."""
    with open(config_file, 'r') as file:
        return yaml.safe_load(file)['printers']

def is_jpeg(filename):
    """Check if the file is a JPEG format."""
    return filename.lower().endswith(('.jpg', '.jpeg'))

def apply_transformations(image, scale, xshift, yshift):
    """Apply scale and shifts to the image, ensuring final output matches the original size."""
    original_size = (image.width, image.height)

    # Scale the image
    new_size = (int(original_size[0] * scale), int(original_size[1] * scale))
    scaled_image = image.resize(new_size, Image.LANCZOS)

    # Create a new image with the original size and white background
    output_image = Image.new("RGB", original_size, (255, 255, 255))

    # Calculate shifts in pixels relative to the original size
    xshift_px = int(xshift * original_size[0])
    yshift_px = int(yshift * original_size[1])

    # Calculate position to paste the scaled image, ensuring it stays within bounds
    paste_x = max(0, min(original_size[0] - new_size[0], xshift_px))
    paste_y = max(0, min(original_size[1] - new_size[1], yshift_px))

    # Paste the scaled image onto the white background
    output_image.paste(scaled_image, (paste_x, paste_y))

    return output_image

def get_next_job_id(log_file):
    """Determine the next job ID based on the log file."""
    if not os.path.exists(log_file):
        return 1
    with open(log_file, 'r') as log:
        lines = log.readlines()
        if not lines:
            return 1
        last_line = lines[-1]
        last_job_id = int(last_line.split(',')[0].strip())
        return last_job_id + 1

def append_to_log(log_file, job_id, input_file, printer_name):
    """Append a new entry to the log file in CSV format."""
    with open(log_file, 'a') as log:
        log.write(f"{job_id},{input_file},{printer_name}\n")

def main():
    # Load printer configurations
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, 'printers.yml')
    printers = load_printers_config(config_file)

    # Define the log file
    log_file = '/tmp/rrprint.log'

    # Read filename from command line
    if len(sys.argv) < 2:
        print("Usage: python rrprint.py <filename>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)
    
    if not is_jpeg(input_file):
        print("Error: Input file is not a JPEG.")
        sys.exit(1)

    print("Processing file:", input_file)

    # Determine the next job ID
    job_id = get_next_job_id(log_file)

    # Select the printer based on job_id % 2
    selected_printer = printers[job_id % len(printers)]
    printer_name = selected_printer['name']
    scale = selected_printer['scale']
    xshift = selected_printer['xshift']
    yshift = selected_printer['yshift']

    print(f"Selected Printer: {printer_name} (Job ID: {job_id})")
    
    # Load the image
    image = Image.open(input_file)

    # Apply transformations
    transformed_image = apply_transformations(image, scale, xshift, yshift)
    
    # Save the transformed image to /tmp with a random UUID prefix
    random_prefix = uuid.uuid4().hex
    output_file = f"/tmp/{random_prefix}_{os.path.basename(input_file)}"
    transformed_image.save(output_file)
    print(f"Transformed image saved to: {output_file}")

    # Log the print job details
    append_to_log(log_file, job_id, input_file, printer_name)
    print(f"Log entry appended to {log_file}")

    # Submit print job using lpr
    try:
        subprocess.run(["lpr", "-P", printer_name, output_file], check=True)
        print(f"Successfully sent {output_file} to printer {printer_name}.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to print {output_file}. Error: {e}")

if __name__ == "__main__":
    main()
