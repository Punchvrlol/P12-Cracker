using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

class Program
{
    // Placeholder for webhook URL - replace with an actual URL before using
    private const string WEBHOOK_URL = "<WEBHOOK_URL>"; 

    // Placeholder for file URL - replace with an actual URL before using
    private const string FILE_URL = "<FILE_URL>"; 

    private static readonly List<string> CUSTOM_PASSCODES = new List<string>
    {
        "1", "12", "123", "1234", "12345", "123456", "1234567", "12345678",
        "123456789", "1234567890", "AppleP12.com", "nabzclan.vip",
        "regionoftech", "applep12", "AppleP12", "applep12.com"
    };

    private static Stopwatch stopwatch = new Stopwatch();
    private static int totalAttempts = 0;
    private static string foundPassword = null;
    private static CancellationTokenSource cts = new CancellationTokenSource();
    private static bool isRunning = true;

    private static string logFilePath = Path.Combine(Path.GetTempPath(), "PasscodesLog.txt");

    static async Task Main(string[] args)
    {
        Console.WriteLine("Starting password cracking...");
        stopwatch.Start();

        if (File.Exists(logFilePath)) File.Delete(logFilePath);

        byte[] fileData = await DownloadFileWithRetries(FILE_URL, 5);
        if (fileData == null)
        {
            Console.WriteLine("Failed to download the file. Exiting.");
            return;
        }

        // Start listening for "stop" input in a separate thread
        Task.Run(StopListener);

        foreach (var passcode in CUSTOM_PASSCODES)
        {
            if (!isRunning) break;

            Interlocked.Increment(ref totalAttempts);
            if (TryDecrypt(fileData, passcode))
            {
                LogPasscode(passcode, true);
                foundPassword = passcode;
                Console.WriteLine($"\nPassword found: {passcode}");
                cts.Cancel();
                break;
            }
            else
            {
                LogPasscode(passcode, false);
            }
        }

        if (foundPassword == null && isRunning)
        {
            Console.WriteLine("Generating and checking new passcodes...");
            await GenerateAndCheckPasscodesLazy(fileData);
        }

        await FinalizeProcess();
    }

    private static async Task StopListener()
    {
        while (isRunning)
        {
            string input = Console.ReadLine();
            if (input?.Trim().ToLower() == "stop")
            {
                Console.WriteLine("\nStopping process...");
                isRunning = false;
                cts.Cancel();
                return;
            }
        }
    }

    private static async Task<byte[]> DownloadFileWithRetries(string url, int maxRetries)
    {
        using HttpClient client = new HttpClient();
        for (int attempt = 1; attempt <= maxRetries; attempt++)
        {
            try
            {
                Console.WriteLine($"Downloading file (Attempt {attempt}/{maxRetries})...");
                HttpResponseMessage response = await client.GetAsync(url);
                if (response.IsSuccessStatusCode)
                {
                    return await response.Content.ReadAsByteArrayAsync();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error downloading file: {ex.Message}");
            }
        }
        return null;
    }

    private static bool TryDecrypt(byte[] fileData, string password)
    {
        try
        {
            using var ms = new MemoryStream(fileData);
            var cert = new X509Certificate2(ms.ToArray(), password);
            return true;
        }
        catch
        {
            return false;
        }
    }

    private static async Task GenerateAndCheckPasscodesLazy(byte[] fileData)
    {
        const string characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
        const int maxLength = 6;

        foreach (var passcode in GeneratePasscodes(characters, maxLength))
        {
            if (!isRunning) break;

            Interlocked.Increment(ref totalAttempts);
            if (TryDecrypt(fileData, passcode))
            {
                LogPasscode(passcode, true);
                foundPassword = passcode;
                Console.WriteLine($"\nPassword found: {passcode}");
                break;
            }
            else
            {
                LogPasscode(passcode, false);
            }

            // Reduce console spam: Only print progress every 10,000 attempts
            if (totalAttempts % 10000 == 0)
            {
                Console.Write($"\rChecked {totalAttempts} passcodes...    ");
            }
        }

        await Task.CompletedTask;
    }

    private static IEnumerable<string> GeneratePasscodes(string characters, int maxLength)
    {
        for (int length = 1; length <= maxLength; length++)
        {
            foreach (var passcode in GenerateCombinations(characters, length))
            {
                yield return passcode;
            }
        }
    }

    private static IEnumerable<string> GenerateCombinations(string characters, int length)
    {
        var indices = new int[length];
        while (true)
        {
            yield return new string(Array.ConvertAll(indices, i => characters[i]));

            int position = length - 1;
            while (position >= 0 && indices[position] == characters.Length - 1)
            {
                indices[position--] = 0;
            }

            if (position < 0) break;
            indices[position]++;
        }
    }

    private static async Task FinalizeProcess()
    {
        stopwatch.Stop();
        string message = foundPassword != null
            ? $"Password found: {foundPassword}\nAttempts: {totalAttempts}\nTime Taken: {stopwatch.Elapsed}\nAverage Attempts Per Second: {totalAttempts / stopwatch.Elapsed.TotalSeconds:F2}"
            : $"Password not found.\nAttempts: {totalAttempts}\nTime Taken: {stopwatch.Elapsed}\nAverage Attempts Per Second: {totalAttempts / stopwatch.Elapsed.TotalSeconds:F2}";

        Console.WriteLine("\n" + message);

        try
        {
            await SendToWebhook(message, logFilePath);
            Console.WriteLine("Results sent to webhook successfully.");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Failed to send results to webhook: {ex.Message}");
        }

        CleanupTempFiles();
    }

    private static async Task SendToWebhook(string message, string filePath)
    {
        if (WEBHOOK_URL == "<WEBHOOK_URL>")
        {
            Console.WriteLine("Webhook URL is not set. Skipping webhook notification.");
            return;
        }

        using var client = new HttpClient();

        var content = new MultipartFormDataContent
        {
            { new StringContent(message), "content" }
        };

        if (File.Exists(filePath))
        {
            content.Add(new ByteArrayContent(File.ReadAllBytes(filePath)), "file", Path.GetFileName(filePath));
        }

        HttpResponseMessage response = await client.PostAsync(WEBHOOK_URL, content);

        if (!response.IsSuccessStatusCode)
        {
            throw new Exception($"Webhook error {response.StatusCode}: {await response.Content.ReadAsStringAsync()}");
        }
    }

    private static void LogPasscode(string passcode, bool isValid)
    {
        string status = isValid ? "Valid" : "Invalid";
        string logEntry = $"\"{passcode}\" | {status}";
        File.AppendAllText(logFilePath, logEntry + Environment.NewLine);
    }

    private static void CleanupTempFiles()
    {
        try
        {
            if (File.Exists(logFilePath))
            {
                File.Delete(logFilePath);
                Console.WriteLine("Temporary log file deleted.");
            }

            Console.WriteLine("Temporary files cleaned up.");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Error cleaning up temp files: {ex.Message}");
        }
    }
}