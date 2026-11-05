from app.services.pptx_renderer import render_pptx_slides

pptx_path = input(
    "Enter the full path of your PPTX file: "
).strip().strip('"')

output_dir = "storage/test_pptx_slides"

try:
    slides = render_pptx_slides(
        pptx_path,
        output_dir
    )

    print("\nPPTX rendering successful!")

    for slide in slides:
        print(
            f"Slide {slide['slide_number']}: "
            f"{slide['image_path']}"
        )

    print(f"\nTotal slides rendered: {len(slides)}")

except Exception as error:
    print(f"\nRendering failed: {error}")