using System;
using System.Threading;
using System.Threading.Tasks;

class Program
{
    static int mineDeposit = 2000;
    static int warehouse = 0;
    static readonly int cartCapacity = 200;

    static SemaphoreSlim depositSemaphore = new SemaphoreSlim(2, 2);
    static SemaphoreSlim warehouseSemaphore = new SemaphoreSlim(1, 1);
    static object lockObject = new object();

    static void Main(string[] args)
    {
        Console.Clear();
        Console.CursorVisible = false;

        int numberOfMiners = 5;
        Task[] miners = new Task[numberOfMiners];

        Task displayTask = Task.Run(() => UpdateGlobalStatus());

        for (int i = 0; i < numberOfMiners; i++)
        {
            int minerId = i + 1;
            miners[i] = Task.Run(() => MinerWork(minerId));
        }

        Task.WaitAll(miners);

        PrintAtLine(0, $"Stan złoża: {mineDeposit} jednostek węgla");
        PrintAtLine(1, $"Stan magazynu: {warehouse} jednostek węgla");
        PrintAtLine(numberOfMiners + 3, "Symulacja zakończona.");
        Console.CursorVisible = true;
    }

    static void UpdateGlobalStatus()
    {
        while (mineDeposit > 0 || warehouse < 2000)
        {
            PrintAtLine(0, $"Stan złoża: {mineDeposit} jednostek węgla");
            PrintAtLine(1, $"Stan magazynu: {warehouse} jednostek węgla");
            Thread.Sleep(100);
        }
        PrintAtLine(0, $"Stan złoża: {mineDeposit} jednostek węgla");
        PrintAtLine(1, $"Stan magazynu: {warehouse} jednostek węgla");
    }

    static void MinerWork(int minerId)
    {
        int line = minerId + 2;

        while (true)
        {
            int minedUnits = 0;

            depositSemaphore.Wait();

            while (minedUnits < cartCapacity)
            {
                bool hasCoal = false;

                lock (lockObject)
                {
                    if (mineDeposit > 0)
                    {
                        mineDeposit--;
                        minedUnits++;
                        hasCoal = true;
                    }
                }

                if (!hasCoal)
                {
                    break;
                }

                PrintAtLine(line, $"Górnik {minerId}: Wydobywa {minedUnits} jednostkę węgla...");
                Thread.Sleep(10);
            }

            depositSemaphore.Release();

            if (minedUnits == 0)
            {
                break;
            }

            PrintAtLine(line, $"Górnik {minerId}: Transportuje do magazynu...");
            Thread.Sleep(10000);

            warehouseSemaphore.Wait();

            PrintAtLine(line, $"Górnik {minerId}: Rozładowuje węgiel...");
            Thread.Sleep(minedUnits * 10);

            lock (lockObject)
            {
                warehouse += minedUnits;
            }

            warehouseSemaphore.Release();

            PrintAtLine(line, $"Górnik {minerId}: Wraca do kopalni...");
            Thread.Sleep(10000);
        }

        PrintAtLine(line, $"Górnik {minerId} zakończył pracę.");
    }

    static void PrintAtLine(int line, string text)
    {
        lock (lockObject)
        {
            Console.SetCursorPosition(0, line);
            Console.Write(text.PadRight(60));
        }
    }
}
