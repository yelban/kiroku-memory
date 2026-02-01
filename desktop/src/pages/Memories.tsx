import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Brain,
  Search,
  Loader2,
  ChevronRight,
  Calendar,
  Tag,
  FileText,
  X,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  getItems,
  getCategories,
  searchMemories,
  type Item,
  type Category,
  type RetrievalResponse,
} from "@/lib/api";

export function MemoriesPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedItem, setSelectedItem] = useState<Item | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<RetrievalResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [itemsData, categoriesData] = await Promise.all([
        getItems({ limit: 100, status: "active" }),
        getCategories(),
      ]);
      setItems(itemsData);
      setCategories(categoriesData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }

    setIsSearching(true);
    try {
      const results = await searchMemories(searchQuery);
      setSearchResults(results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
    } finally {
      setIsSearching(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const clearSearch = () => {
    setSearchQuery("");
    setSearchResults(null);
  };

  // Filter items by category
  const displayItems = searchResults
    ? searchResults.items
    : selectedCategory
      ? items.filter((item) => item.category === selectedCategory)
      : items;

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString("zh-TW", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return "text-green-500";
    if (confidence >= 0.5) return "text-yellow-500";
    return "text-red-500";
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex gap-4 h-[calc(100vh-140px)]">
      {/* Left Panel: List */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Search Bar */}
        <Card className="mb-4">
          <CardContent className="p-3">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="搜尋記憶..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="pl-9 pr-9"
                />
                {searchQuery && (
                  <button
                    onClick={clearSearch}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>
              <Button onClick={handleSearch} disabled={isSearching}>
                {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : "搜尋"}
              </Button>
              <Button variant="ghost" size="icon" onClick={loadData}>
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>

            {/* Category Filters */}
            {categories.length > 0 && !searchResults && (
              <div className="flex gap-2 mt-3 flex-wrap">
                <Badge
                  variant={selectedCategory === null ? "default" : "outline"}
                  className="cursor-pointer"
                  onClick={() => setSelectedCategory(null)}
                >
                  全部
                </Badge>
                {categories.map((cat) => (
                  <Badge
                    key={cat.id}
                    variant={selectedCategory === cat.name ? "default" : "outline"}
                    className="cursor-pointer"
                    onClick={() => setSelectedCategory(cat.name)}
                  >
                    {cat.name}
                  </Badge>
                ))}
              </div>
            )}

            {/* Search Results Info */}
            {searchResults && (
              <div className="mt-3 text-sm text-muted-foreground">
                找到 {searchResults.total_items} 筆結果
                <button onClick={clearSearch} className="ml-2 text-primary hover:underline">
                  清除搜尋
                </button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm">{error}</div>
        )}

        {/* Items List */}
        <Card className="flex-1 overflow-hidden">
          <CardHeader className="py-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Brain className="w-4 h-4" />
              {searchResults ? "搜尋結果" : "記憶項目"}
              <span className="text-muted-foreground font-normal">({displayItems.length})</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 overflow-auto h-[calc(100%-60px)]">
            {displayItems.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Brain className="w-12 h-12 mb-4 opacity-20" />
                <p>{searchResults ? "沒有找到相關記憶" : "尚無記憶項目"}</p>
              </div>
            ) : (
              <div className="divide-y divide-border">
                {displayItems.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setSelectedItem(item)}
                    className={cn(
                      "w-full text-left p-4 hover:bg-muted/50 transition-colors flex items-start gap-3",
                      selectedItem?.id === item.id && "bg-muted"
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">
                        {item.subject || "(無主題)"}
                      </div>
                      <div className="text-sm text-muted-foreground truncate mt-0.5">
                        {item.predicate} {item.object}
                      </div>
                      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {formatDate(item.created_at)}
                        </span>
                        {item.category && (
                          <span className="flex items-center gap-1">
                            <Tag className="w-3 h-3" />
                            {item.category}
                          </span>
                        )}
                        <span className={cn("tabular-nums", getConfidenceColor(item.confidence))}>
                          {Math.round(item.confidence * 100)}%
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 mt-1" />
                  </button>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Right Panel: Detail */}
      <Card className="w-80 shrink-0">
        <CardHeader className="py-3">
          <CardTitle className="text-base flex items-center gap-2">
            <FileText className="w-4 h-4" />
            詳細資訊
          </CardTitle>
        </CardHeader>
        <CardContent>
          {selectedItem ? (
            <div className="space-y-4">
              <div>
                <div className="text-xs text-muted-foreground mb-1">主詞</div>
                <div className="font-medium">{selectedItem.subject || "-"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">述詞</div>
                <div>{selectedItem.predicate || "-"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">受詞</div>
                <div>{selectedItem.object || "-"}</div>
              </div>
              <div className="border-t border-border pt-4">
                <div className="text-xs text-muted-foreground mb-1">分類</div>
                <div>{selectedItem.category ? <Badge>{selectedItem.category}</Badge> : "-"}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">信心度</div>
                <div className={cn("font-mono", getConfidenceColor(selectedItem.confidence))}>
                  {Math.round(selectedItem.confidence * 100)}%
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">狀態</div>
                <Badge variant={selectedItem.status === "active" ? "default" : "secondary"}>
                  {selectedItem.status}
                </Badge>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">建立時間</div>
                <div className="text-sm">{new Date(selectedItem.created_at).toLocaleString("zh-TW")}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">ID</div>
                <div className="text-xs font-mono text-muted-foreground break-all">{selectedItem.id}</div>
              </div>
            </div>
          ) : (
            <div className="text-center text-muted-foreground py-8">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-20" />
              <p className="text-sm">選擇一個項目查看詳細資訊</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
