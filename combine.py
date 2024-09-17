import cv2
import os

# Directory containing images
image_folder = 'C:/Users/khank/OneDrive/Desktop'  # Replace with the path to your images
# Output video file name
output_video = 'C:/Users/khank/OneDrive/Desktop/output_video.mp4'
# Desired video resolution (width, height)
output_resolution = (640, 360)  # Example resolution

# Function to resize an image while maintaining aspect ratio
def resize_image(image, target_resolution):
    h, w = image.shape[:2]
    target_w, target_h = target_resolution

    # Compute scaling factors
    scale_w = target_w / w
    scale_h = target_h / h
    scale = min(scale_w, scale_h)

    # Resize the image to maintain the aspect ratio
    new_size = (int(w * scale), int(h * scale))
    resized_image = cv2.resize(image, new_size)

    # Create a new blank image with the target resolution
    top_padding = (target_h - new_size[1]) // 2
    bottom_padding = target_h - new_size[1] - top_padding
    left_padding = (target_w - new_size[0]) // 2
    right_padding = target_w - new_size[0] - left_padding

    result_image = cv2.copyMakeBorder(
        resized_image, 
        top_padding, bottom_padding, left_padding, right_padding, 
        cv2.BORDER_CONSTANT, value=[0, 0, 0]
    )
    return result_image

# Get a list of image files in the folder
images = [img for img in os.listdir(image_folder) if img.endswith(".png")]
images.sort()  # Sort the images by name, modify as needed

# Initialize video writer
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for mp4
fps = 10  # Frames per second
out = cv2.VideoWriter(output_video, fourcc, fps, output_resolution)

# Process each image
for image_file in images:
    img_path = os.path.join(image_folder, image_file)
    img = cv2.imread(img_path)

    # Ensure the image is loaded properly
    if img is None:
        print(f"Warning: Could not load image {img_path}")
        continue

    # Resize image to match the output resolution
    resized_img = resize_image(img, output_resolution)

    # Write the resized image as a frame to the video
    out.write(resized_img)

# Release the video writer
out.release()
print(f'Video saved as {output_video}')
