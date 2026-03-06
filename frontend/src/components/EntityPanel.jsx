import React from 'react';
import { Tag, ShoppingBag, ExternalLink } from 'lucide-react';

export default function EntityPanel({ intent, entities }) {
    if (!entities || entities.length === 0) {
        return (
            <div className="bg-zinc-900/50 rounded-2xl p-6 ring-1 ring-zinc-800/50 text-center">
                <p className="text-zinc-500 text-sm">No shoppable items detected in this reel.</p>
            </div>
        );
    }

    const getIntentBadge = () => {
        if (!intent?.category && !intent?.description) return null;

        // Format category nicely
        const formattedCategory = intent.category
            ? intent.category.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')
            : 'Topic';

        return (
            <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-indigo-500/10 text-indigo-400 rounded-full text-xs font-medium border border-indigo-500/20 mb-4">
                <Tag className="w-3.5 h-3.5" />
                {formattedCategory} · {intent.description || 'Intent detected'}
            </div>
        );
    };

    return (
        <div className="bg-zinc-900/50 rounded-2xl p-6 ring-1 ring-zinc-800/50">
            <h3 className="font-semibold text-zinc-100 flex items-center gap-2 mb-4">
                <ShoppingBag className="w-4 h-4 text-indigo-400" />
                Intent-matched items
            </h3>

            {getIntentBadge()}

            <div className="max-h-[300px] overflow-y-auto pr-2 space-y-3 custom-scrollbar">
                {entities.map((entity, idx) => {
                    const confidence = entity.confidence || 0.5;
                    const opacityClass = confidence > 0.8 ? 'opacity-100' : (confidence > 0.6 ? 'opacity-80' : 'opacity-60');
                    const weightClass = confidence > 0.8 ? 'font-bold' : 'font-semibold';

                    return (
                        <div key={entity.id || idx} className={`bg-zinc-800/50 hover:bg-zinc-800 transition-colors p-4 rounded-xl border border-zinc-700/50 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between group ${opacityClass}`}>
                            <div className="flex-1">
                                <div className="flex items-center gap-2 mb-1">
                                    <span className={`text-slate-200 ${weightClass} text-sm`}>{entity.name}</span>
                                    {entity.brand && (
                                        <span className="px-2 py-0.5 bg-zinc-700 text-zinc-300 rounded text-[10px] uppercase font-bold tracking-wider">
                                            {entity.brand}
                                        </span>
                                    )}
                                </div>

                                <div className="flex items-center gap-2 mt-2">
                                    <span className="text-xs text-zinc-400 bg-zinc-900 px-2 py-1 rounded-md border border-zinc-800 capitalize">
                                        {entity.sub_category || entity.type}
                                    </span>
                                    {entity.notes && (
                                        <span className="text-xs text-zinc-500 line-clamp-1">{entity.notes}</span>
                                    )}
                                </div>
                            </div>

                            <button
                                onClick={() => console.log(entity.search_query)}
                                className="shrink-0 px-4 py-2 bg-zinc-700 text-white hover:bg-indigo-600 hover:text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 opacity-0 group-hover:opacity-100 focus:opacity-100 outline-none"
                            >
                                Find Deals <ExternalLink className="w-3 h-3" />
                            </button>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
