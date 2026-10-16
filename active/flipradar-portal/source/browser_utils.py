def block_heavy_resources(context):
    """
    Do skanowania OLX nie potrzebujemy:
    - zdjęć,
    - filmów,
    - fontów.

    HTML, JS, XHR i CSS zostają.
    """

    def handle_route(route):

        resource_type = (
            route.request.resource_type
        )

        if resource_type in {
            "image",
            "media",
            "font",
        }:
            route.abort()

        else:
            route.continue_()

    context.route(
        "**/*",
        handle_route
    )
