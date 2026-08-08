#include <stdio.h>

int main() {
    float num1, num2, sum;
    char choice;

    // Run the loop continuously
    while (1) {
        // Prompt the user for the first number
        printf("Enter the first 32-bit floating-point number: ");
        // %f is used to read a standard 32-bit float
        if (scanf("%f", &num1) != 1) {
            printf("Invalid input. Exiting program...\n");
            break;
        }

        // Prompt the user for the second number
        printf("Enter the second 32-bit floating-point number: ");
        if (scanf("%f", &num2) != 1) {
            printf("Invalid input. Exiting program...\n");
            break;
        }

        # Perform addition
        sum = num1 + num2;

        // Display the result
        printf("Result: %.2f + %.2f = %.2f\n\n", num1, num2, sum);

        // Ask the user if they want to continue
        printf("Do you want to perform another addition? (y/n): ");
        // The space before %c is crucial to consume any leftover newline characters
        scanf(" %c", &choice);

        // Check if the user wants to exit
        if (choice == 'n' || choice == 'N') {
            printf("Exiting program. Goodbye!\n");
            break; // Exit the while loop
        }

        printf("\n-----------------------------------\n\n");
    }

    return 0;
}
